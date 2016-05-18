# Copyright (C) 2016  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
''' That's what happens when you run Craftr. '''

import craftr
from craftr import *
from craftr import shell

import argparse
import atexit
import errno
import importlib
import os
import textwrap
import time
import shutil
import subprocess
import sys

from functools import partial


def _set_env(defs, main_module_name):
  ''' This function updates the environment variables based on a list
  of strings of the format `KEY=VALUE` where each subsequent part is
  optional. The following behaviour applies:

  - `KEY`: Assigns a value of `'true'` to the specified key
  - `KEY=`: Deletes the specified key from the environment
  - `KEY=VALUE`: Sets the specified key to the specified value.

  If the key is prefixed with a dot, it is prefixed with the current
  main modules name.
  '''

  for item in defs:
    key, assign, value = item.partition('=')
    if assign and not value:
      environ.pop(key, None)
      continue
    elif not assign:
      value = 'true'
    if key.startswith('.'):
      key = main_module_name + key
    environ[key] = value


def _abs_env(cwd=None):
  ''' Converts relative paths in the process environment to absolute
  paths. This is necessary since Craftr switches to another working
  directory during execution. See craftr-build/craftr#33 . '''

  cwd = path.abspath(cwd) if cwd else os.getcwd()
  def mk_abs(value):
    # Actually on Windows, there are variables like HOMEDRIVE and
    # SYSTEMDRIVE that look like 'C:' (without trailing backslash)
    # and these are not seen as absolute paths and path.join()
    # also bugs out.
    if os.name == 'nt':
      if len(value) == 2 and value[1] == ':':
        # Just a drive letter.
        return value
    if not path.isabs(value):
      test_path = path.normpath(path.join(cwd, value))
      if path.exists(test_path):
        return test_path
    return value

  for key, value in list(environ.items()):
    if key == 'PATH':
      value = path.pathsep.join(map(mk_abs, value.split(path.pathsep)))
    else:
      value = mk_abs(value)
    environ[key] = value


def main():
  parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=textwrap.dedent('''
    Craftr v{}
    -----------------

    Craftr is the next generation build system based on Ninja and Python.

    https://github.com/craftr-build/craftr
    '''.format(craftr.__version__)))
  parser.add_argument('-V', action='store_true', help='print version and exit ({})'.format(craftr.__version__))
  parser.add_argument('-v', action='count', default=0, help='increase the verbosity level')
  parser.add_argument('-m', metavar='MODULE', help='name of the main Craftr module to take relative target references for or the module to load if no targets are specified on the command-line')
  parser.add_argument('-n', action='store_true', help='skip the build step')
  parser.add_argument('-e', action='store_true', help='(re-)export the Ninja manifest')
  parser.add_argument('-b', action='store_true', help='deprecated since v1.1.0')
  parser.add_argument('-c', default=0, action='count', help='clean the specified target(s), or clean everything with -cc')
  parser.add_argument('-d', metavar='BUILDDIR', help='build directory, defaults to "./build" or the cwd if -p is used (conflicts with -p)')
  parser.add_argument('-p', metavar='PROJECTDIR', help='inverse of -b, use the specified directory as the main project directory and the cwd for -b')
  parser.add_argument('-D', metavar='<key>[=<value>]', default=[], action='append',
    help='set an option in the environment variable, <key> may be relative, '
    '=<value> can be omitted')
  parser.add_argument('-I', metavar='PATH', default=[], action='append', help='additional Craftr module search path')
  parser.add_argument('-N', nargs='...', default=[], help='additional args passed to the Ninja command-line')
  parser.add_argument('--no-rc', action='store_true', help='skip running craftrc.py files')
  parser.add_argument('--rc', metavar='.PY', help='run the specified Python file before anything else, CAN be paired with --no-rc')
  parser.add_argument('--strace-depth', metavar='INT', type=int, default=5, help='depth of the logging stacktrace, default is 5')
  parser.add_argument('--rts', action='store_true', help='keep alive the runtime server')
  parser.add_argument('--rts-at', metavar='HOST:PORT', type=craftr.rts.parse_uri, help='override the runtime server\'s host:port')
  parser.add_argument('targets', nargs='*', default=[], help='zero or more target/task names to build/execute')
  args = parser.parse_args()
  debug = partial(craftr.debug, verbosity=args.v)

  if args.b:
    warn('"-b" option is deprecated (since v1.1.0)')

  if args.V:
    print('craftr {0}'.format(craftr.__version__))
    return 0

  if not args.d:
    if args.p:
      debug('using "." as build directory (-p)')
      args.d = os.getcwd()
    else:
      args.d = 'build'
  if not args.p:
    args.p = os.getcwd()

  # Normalize the search path directories.
  args.I = path.normpath(args.I)

  if not args.m:
    cfile = path.join(args.p, 'Craftfile.py')
    if not path.isfile(cfile):
      error('{0!r} does not exist'.format(path.relpath(cfile)))
      return errno.ENOENT
    args.m = craftr.ext.get_module_ident(cfile)
    if not args.m:
      error('{0!r} has no or an invalid craftr_module(...) declaration'.format(
        path.relpath(cfile)))
      return errno.ENOENT

  build_dir_exists = os.path.isdir(args.d)
  if not path.exists(args.d):
    os.makedirs(args.d)
  elif not path.isdir(args.d):
    error('"{0}" is not a directory'.format(args.d))
    return errno.ENOTDIR

  try:
    ninja_ver = craftr.ninja.get_ninja_version()
  except OSError as exc:
    error('Ninja could not be found. Goto https://ninja-build.org/')
    return errno.ENOENT
  debug('detected ninja v{0}'.format(ninja_ver))

  # Convert relative to absolute target names.
  mkabst = lambda x: ((args.m + x) if (x.startswith('.')) else x).replace(':', '.')
  args.targets = [mkabst(x) for x in args.targets]

  old_cwd = path.normpath(args.p)
  if os.getcwd() != path.normpath(args.d):
    started_from_build_dir = False
    os.chdir(args.d)
    debug('$ cd "{0}"'.format(args.d))

  # If the build directory didn't exist from the start and it
  # is empty after Craftr exits, we can delete it again.
  @atexit.register
  def _delete_build_dir():
    os.chdir(old_cwd)
    if not build_dir_exists and not os.listdir(args.d):
      os.rmdir(args.d)

  rts_mode = None
  cache = None
  do_run = bool(args.e or args.rts)
  export_if_required = False
  if args.e:
    # Remove files/directories we'll create again eventually.
    path.silent_remove(craftr.MANIFEST)
    path.silent_remove(craftr.CMDDIR, is_dir=True)
  elif not path.isfile(craftr.MANIFEST):
    # We need to export a manifest if its required by the selected targets.
    export_if_required = do_run = True
  else:
    # If we're not going to export a manifest, read the cached
    # data from the Ninja manifest.
    cache = craftr.ninja.CraftrCache.read()

    # Make sure all targets exist in the cache.
    for target in args.targets:
      if target not in cache.targets:
        error('target {!r} does not exist in cache'.format(target))
        return errno.ENOENT

    # If any of the targets require the RTS feature, we still need
    # to execute the Craftr module.
    rts_mode = cache.get_rts_mode(args.targets)
    if rts_mode != Target.RTS_None:
      info('can not skip execution, one or more targets are tasks')
      do_run = True
    else:
      info('skipping execution phase')

    # Prepend the options that were specified when the manifest
    # was exported.
    if cache.options:
      info('prepending cached options:', ' '.join(
        shell.quote('-D' + x) for x in cache.options))
      args.D = cache.options + args.D

    # Same for the search path.
    if cache.path:
      info('prepending cached search path:', ' '.join(
        shell.quote('-I' + x) for x in cache.path))
      args.I = cache.path + args.I

  session = craftr.Session(
    cwd=old_cwd,
    path=[old_cwd] + args.I,
    server_bind=args.rts_at,
    verbosity=args.v,
    strace_depth=args.strace_depth,
    export=args.e)
  with craftr.magic.enter_context(craftr.session, session):
    _abs_env(old_cwd)

    if do_run:
      # Run the environment files.
      if not args.no_rc:
        session.exec_if_exists(path.normpath('~/craftrc.py'))
        session.exec_if_exists(path.join(old_cwd, 'craftrc.py'))
      if args.rc:
        rc_file = path.normpath(args.rc, old_cwd)
        if not session.exec_if_exists(rc_file):
          error('--rc {0!r} does not exist'.format(args.rc))
          return errno.ENOENT

      _set_env(args.D, args.m)
      _abs_env(old_cwd)

      try:
        if not args.targets:
          # Load the main craftr module specified via the -m option
          # or the "Craftfile.py" of the original cwd.
          debug('load {!r}'.format('craftr.ext.' + args.m))
          importlib.import_module('craftr.ext.' + args.m)
        else:
          # Load the targets specified on the command-line.
          for tname in args.targets:
            mname = tname.rpartition('.')[0]
            if mname and mname not in session.modules:
              debug('load {!r}'.format('craftr.ext.' + mname))
              importlib.import_module('craftr.ext.' + mname)
      except craftr.ModuleError as exc:
        error('Error in module {0!r}. Abort'.format(exc.module.project_name))
        return 1
      except ImportError as exc:
        error(exc)
        return errno.ENOENT

      try:
        targets = [session.targets[x] for x in args.targets]
      except KeyError as key:
        error('Target {0} does not exist'.format(key))
        return errno.ENOENT

      session.finalize()
      cache = craftr.ninja.CraftrCache(args.D, args.I, session=session)
      if rts_mode is None:
        rts_mode = cache.get_rts_mode(args.targets)

      if export_if_required and rts_mode != Target.RTS_Plain:
        warn('{!r} does not exist but is required by selected targets, forcing "-e"'.format(craftr.MANIFEST))
        args.e = True

      if args.e:
        # Export a ninja manifest.
        debug('exporting {!r}'.format(craftr.MANIFEST))
        with open(craftr.MANIFEST, 'w') as fp:
          craftr.ninja.export(fp, cache)
    else:
      _set_env(args.D, args.m)
      _abs_env(old_cwd)

    if rts_mode is None:
      rts_mode = cache.get_rts_mode(args.targets)

    # If the session has targets that require the RTS feature or
    # if the --rts flag was specified, start the RTS server.
    if args.rts or rts_mode != Target.RTS_None:
      session.start_server()

    # Perform a full or rule-based clean.
    if args.c:
      cmd = ['ninja', '-t', 'clean']
      if args.c == 1:
        # Non-recursive clean.
        cmd.append('-r')
      cmd += (t for t in args.targets)
      debug("$", shell.join(cmd))
      ret = shell.run(cmd, shell=True, check=False).returncode
      if ret != 0:
        return ret

    # Perform the build.
    if not args.n:
      if rts_mode == Target.RTS_Plain:
        debug("the specified targets can be executed in plain Python-space")
        state = {}
        try:
          for target in args.targets:
            session.targets[target].execute_task(state)
        except craftr.TaskError as exc:
          error(exc)
          return exc.result
      else:
        cmd = ['ninja'] + [t for t in args.targets] + args.N
        debug("$", shell.join(cmd))
        ret = shell.run(cmd, shell=True, check=False).returncode
        if ret != 0:
          return ret

    if args.rts:
      try:
        info('Craftr RTS alive at {0}. Use CTRL+C to stop.'.format(environ['CRAFTR_RTS']))
        while True:
          time.sleep(1)
      except KeyboardInterrupt:
        print(file=sys.stderr)
        info('Craftr RTS stopped. Bye bye')
    return 0


if __name__ == '__main__':
  sys.exit(main())


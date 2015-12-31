# Copyright (C) 2015  Niklas Rosenstein
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

from craftr import *
from craftr import shell

import argparse
import craftr
import errno
import importlib
import os
import subprocess
import sys


def _set_env(defs):
  ''' This function updates the environment variables based on a list
  of strings of the format `KEY=VALUE` where each subsequent part is
  optional. The following behaviour applies:

  - `KEY`: Assigns a value of `'true'` to the specified key
  - `KEY=`: Deletes the specified key from the environment
  - `KEY=VALUE`: Sets the specified key to the specified value.
  '''

  for item in defs:
    key, assign, value = item.partition('=')
    if assign and not value:
      environ.pop(key, None)
      continue
    elif not assign:
      value = 'true'
    environ[key] = value


def _abs_env(cwd=None):
  ''' Converts relative paths in the process environment to absolute
  paths. This is necessary since Craftr switches to another working
  directory during execution. See craftr-build/craftr#33 . '''

  cwd = path.abspath(cwd) if cwd else os.getcwd()
  def mk_abs(item):
    if not path.isabs(item) and path.exists(item):
      return path.join(cwd, item)
    return item

  for key, value in list(environ.items()):
    if key == 'PATH':
      value = path.sep.join(map(mk_abs, value.split(path.sep)))
    else:
      value = mk_abs(value)
    environ[key] = value


def _run_func(main_module, name, args):
  ''' Called to run a function with the specified *name* and set
  `sys.argv` to *args*. If *name* is a relative identifier, it will
  be searched relative to the *main_module* name. '''

  if '.' not in name:
    name = main_module + '.' + name
  module_name, func_name = name.rsplit('.', 1)
  if module_name not in session.modules:
    error('no module "{0}" was loaded'.format(module_name))
    return errno.ENOENT
  module = session.modules[module_name]
  if not hasattr(module, func_name):
    error('module "{0}" has no member "{1}"'.format(module_name, func_name))
    return errno.ENOENT
  func = getattr(module, func_name)
  if not callable(func):
    error('"{0}" is not callable'.format(name))
    return errno.ENOENT
  old_argv = sys.argv
  sys.argv = ['craftr -f {0}'.format(name)] + args
  try:
    func()
  except SystemExit as exc:
    return exc.errno
  finally:
    sys.argv = old_argv
  return 0


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-V', action='store_true', help='Print version and exit.')
  parser.add_argument('-v', action='count', default=0, help='Increase the verbosity level.')
  parser.add_argument('-m', help='The name of a Craftr module to run.')
  parser.add_argument('-e', action='store_true', help='Export the build definitions to build.ninja')
  parser.add_argument('-b', action='store_true', help='Build all or the specified targets. Note that no Craftr modules are executed, if that is not required by other options.')
  parser.add_argument('-c', default=0, action='count', help='Clean the targets before building. Clean recursively on -cc')
  parser.add_argument('-d', default='build', help='The build directory')
  parser.add_argument('-D', default=[], action='append', help='Set an option, is automatically converted to the closest applicable datatype')
  parser.add_argument('-f', nargs='+', help='The name of a function to execute.')
  parser.add_argument('-F', nargs='+', help='The name of a function to execute, AFTER the build process if any.')
  parser.add_argument('-N', nargs='...', default=[], help='Additional args to pass to ninja')
  parser.add_argument('--daemon', type=craftr.daemon.parse_uri, help='Keep the Craftr daemon running under the specified host:port')
  parser.add_argument('--no-rc', action='store_true', help='Do not run Craftr startup files.')
  parser.add_argument('--rc', help='Execute the specified Craftr startup file. CAN be paired with --no-rc')
  parser.add_argument('--strace-depth', type=int, default=3, help='Depth of logging stack trace. Defaults to 3')
  parser.add_argument('targets', nargs='*', default=[])
  args = parser.parse_args()

  if args.V:
    print('Craftr {0}'.format(craftr.__version__))
    return 0

  if not args.m:
    if not path.isfile('Craftfile'):
      error('"Craftfile" does not exist')
      return errno.ENOENT
    args.m = craftr.ext.get_module_ident('Craftfile')
    if not args.m:
      error('"Craftfile" has no or an invalid craftr_module(...) declaration')
      return errno.ENOENT

  if not path.exists(args.d):
    os.makedirs(args.d)
  elif not path.isdir(args.d):
    error('"{0}" is not a directory'.format(args.d))
    return errno.ENOTDIR

  try:
    craftr.ninja.get_ninja_version()
  except OSError as exc:
    error('ninja is not installed on the system')
    return errno.ENOENT

  # Convert relative to absolute target names.
  mkabst = lambda x: ((args.m + '.' + x) if ('.' not in x) else x).replace(':', '.')
  args.targets = [mkabst(x) for x in args.targets]

  old_cwd = os.getcwd()
  os.chdir(args.d)

  # Check if we should omit the execution step. This is possile when
  # we the -b option is specified and NOT -c == 1, -e, -f or -F.
  do_run = any([args.e, args.f, args.F, args.daemon])
  if not do_run and not args.b:
    # Do nothing at all? Then do the execution step.
    do_run = True

  if not do_run:
    info("skipping execution phase.")

  session = craftr.Session(cwd=old_cwd, path=[old_cwd], daemon_bind=args.daemon)
  with craftr.magic.enter_context(craftr.session, session):
    _abs_env(old_cwd)

    # Initialize the session settings from the command-line parameters.
    session.verbosity = args.v
    session.strace_depth = args.strace_depth

    if do_run:
      # Run the environment files.
      if not args.no_rc:
        session.exec_if_exists(path.normpath('~/.craftrc'))
        session.exec_if_exists(path.join(old_cwd, '.craftrc'))
      if args.rc:
        rc_file = path.normpath(args.rc, old_cwd)
        if not session.exec_if_exists(rc_file):
          error('--rc {0!r} does not exist'.format(args.rc))
          return errno.ENOENT

      _set_env(args.D)
      _abs_env(old_cwd)

      # Load the main craftr module specified via the -m option
      # or the "Craftfile" of the original cwd.
      try:
        module = importlib.import_module('craftr.ext.' + args.m)
      except craftr.ModuleError as exc:
        error('error in module {0!r}. Abort'.format(exc.module.project_name))
        return 1

      if args.f:
        # Pre-build function.
        with craftr.magic.enter_context(craftr.module, module):
          _run_func(args.m, args.f[0], args.f[1:])

      try:
        targets = [session.targets[x] for x in args.targets]
      except KeyError as key:
        error('Target "{0}" does not exist'.format(key))
        return errno.ENOENT

      if args.e:
        # Export a ninja manifest.
        with open('build.ninja', 'w') as fp:
          craftr.ninja.export(fp, module)
    else:
      _set_env(args.D)
      _abs_env(old_cwd)

    if args.c:
      cmd = ['ninja', '-t', 'clean']
      if args.c == 1:
        # Non-recursive clean.
        cmd.append('-r')
      cmd += (t for t in args.targets)
      ret = shell.run(cmd, shell=True, check=False).returncode
      if ret != 0:
        return ret

    # Execute the build.
    if args.b:
      cmd = ['ninja'] + [t for t in args.targets] + args.N
      ret = shell.run(cmd, shell=True, check=False).returncode
      if ret != 0:
        return ret

    if args.F:
      # Post-build function.
      assert do_run
      with craftr.magic.enter_context(craftr.module, module):
        _run_func(args.m, args.F[0], args.F[1:])

    if args.daemon:
      try:
        info('Kepping Craftr daemon alive.')
        while True:
          time.sleep(1)
      except KeyboardInterrupt:
        print(file=sys.stderr)
        info('Quit.')
    return 0


if __name__ == '__main__':
  sys.exit(main())


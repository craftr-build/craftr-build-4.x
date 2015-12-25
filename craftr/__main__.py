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

from craftr import session, shell, path

import argparse
import craftr
import errno
import importlib
import os
import subprocess
import sys


def _set_env(defs):
  for item in defs:
    key, assign, value = item.partition('=')
    if assign and not value:
      os.environ.pop(key, None)
      continue
    elif not assign:
      value = 'true'
    os.environ[key] = value


def _abs_env():
  def mk_abs(item):
    if not path.isabs(item) and path.exists(item):
      return path.abspath(item)
    return item
  for key, value in list(os.environ.items()):
    if key == 'PATH':
      value = path.sep.join(map(mk_abs, value.split(path.sep)))
    else:
      value = mk_abs(value)
    os.environ[key] = value


def _run_func(main_module, name, args):
  if '.' not in name:
    name = main_module + '.' + name
  module_name, func_name = name.rsplit('.', 1)
  if module_name not in session.modules:
    print('craftr: error: no module "{0}" was loaded'.format(module_name))
    return errno.ENOENT
  module = session.modules[module_name]
  if not hasattr(module, func_name):
    print('craftr: error: module "{0}" has no member "{1}"'.format(module_name, func_name))
    return errno.ENOENT
  func = getattr(module, func_name)
  if not callable(func):
    print('craftr: error: "{0}" is not callable'.format(name))
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
  parser.add_argument('-m', help='The name of a Craftr module to run.')
  parser.add_argument('-e', action='store_true', help='Export the build definitions to build.ninja')
  parser.add_argument('-b', action='store_true', help='Build all or the specified targets. Note that no Craftr modules are executed, if that is not required by other options.')
  parser.add_argument('-c', default=0, action='count', help='Clean the targets before building. Clean recursively on -cc')
  parser.add_argument('-d', default='build', help='The build directory')
  parser.add_argument('-D', default=[], action='append', help='Set an option, is automatically converted to the closest applicable datatype')
  parser.add_argument('-f', nargs='+', help='The name of a function to execute.')
  parser.add_argument('-F', nargs='+', help='The name of a function to execute, AFTER the build process if any.')
  parser.add_argument('-N', nargs='...', default=[], help='Additional args to pass to ninja')
  parser.add_argument('--no-env', action='store_true', help='Do not run Craftr environment files.')
  parser.add_argument('--env', help='Execute the specified Craftr environment file. CAN be paired with --no-env')
  parser.add_argument('targets', nargs='*', default=[])
  args = parser.parse_args()

  if args.V:
    print('Craftr {0}'.format(craftr.__version__))
    return 0

  if not args.m:
    if not path.isfile('Craftfile'):
      print('craftr: error: "Craftfile" does not exist')
      return errno.ENOENT
    args.m = craftr.ext.get_module_ident('Craftfile')
    if not args.m:
      print('craftr: error: "Craftfile" has no craftr_module(...) declaration')
      return errno.ENOENT

  if not path.exists(args.d):
    os.makedirs(args.d)
  elif not path.isdir(args.d):
    print('craftr: error: "{0}" is not a directory'.format(args.d))
    return errno.ENOTDIR

  try:
    craftr.ninja.get_ninja_version()
  except OSError as exc:
    print('craftr: error: ninja is not installed on the system')
    return errno.ENOENT

  # Convert relative to absolute target names.
  args.targets = [
    (args.m + '.' + t) if ('.' not in t) else t for t in args.targets]

  _set_env(args.D)
  _abs_env()
  old_cwd = os.getcwd()
  os.chdir(args.d)

  # Check if we should omit the execution step. This is possile when
  # we the -b option is specified and NOT -c == 1, -e, -f or -F.
  do_run = not args.b or any([args.c == 1, args.e, args.f, args.F])
  if not do_run:
    print("craftr: skipping execution phase.")

  session_obj = craftr.Session(cwd=old_cwd, path=[old_cwd])
  with craftr.magic.enter_context(session, session_obj):
    if do_run:
      # Run the environment files.
      if not args.no_env:
        session.exec_if_exists(path.normpath('~/Craftenv'))
        session.exec_if_exists(path.join(old_cwd, 'Craftenv'))
      if args.env:
        env_file = path.normpath(args.env, old_cwd)
        if not session.exec_if_exists(env_file):
          print('craftr: error: --env {0!r} does not exist'.format(args.env))
          return errno.ENOENT

      # Load the main craftr module specified via the -m option
      # or the "Craftfile" of the original cwd.
      module = importlib.import_module('craftr.ext.' + args.m)

      if args.f:
        # Pre-build function.
        with craftr.magic.enter_context(craftr.module, module):
          _run_func(args.m, args.f[0], args.f[1:])

      try:
        targets = [session.targets[x] for x in args.targets]
      except KeyError as key:
        print('craftr: error: Target "{0}" does not exist'.format(key))
        return errno.ENOENT

      if args.e:
        # Export a ninja manifest.
        with open('build.ninja', 'w') as fp:
          craftr.ninja.export(fp, module)

    if args.c:
      cmd = ['ninja', '-t', 'clean']
      if args.c == 1:
        # Non-recursive clean.
        cmd.append('-r')
      cmd += (t for t in args.targets)
      ret = shell.call(cmd, shell=True)
      if ret != 0:
        return ret

    # Execute the build.
    if args.b:
      cmd = ['ninja'] + [t for t in args.targets] + args.N
      ret = shell.call(cmd, shell=True)
      if ret != 0:
        return ret

    if args.F:
      # Post-build function.
      assert do_run
      with craftr.magic.enter_context(craftr.module, module):
        _run_func(args.m, args.F[0], args.F[1:])

    return 0


if __name__ == '__main__':
  sys.exit(main())

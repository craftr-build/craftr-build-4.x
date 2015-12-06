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

from craftr import session

import argparse
import craftr
import errno
import importlib
import os
import subprocess


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-m', help='The name of a Craftr module to run.')
  parser.add_argument('-e', action='store_true', help='Export the build definitions to build.ninja')
  parser.add_argument('-b', action='store_true', help='Build all or the specified targets.')
  parser.add_argument('-c', default=0, action='count', help='Clean the targets before building. Clean recursively on -cc')
  parser.add_argument('-d', default='build', help='The build directory')
  parser.add_argument('targets', nargs='*', default=[])
  args = parser.parse_args()

  if not args.m:
    if not os.path.isfile('Craftfile'):
      print('error: "Craftfile" does not exist')
      return errno.ENOENT
    args.m = craftr.ext.get_module_ident('Craftfile')
    if not args.m:
      print('error: "Craftfile" has no craftr_module(...) declaration')
      return errno.ENOENT

  if not os.path.exists(args.d):
    os.makedirs(args.d)
  elif not os.path.isdir(args.d):
    print('error: "{0}" is not a directory'.format(args.d))
    return errno.ENOTDIR

  try:
    craftr.ninja.get_ninja_version()
  except OSError as exc:
    print('error: ninja is not installed on the system')
    return errno.ENOENT

  old_path = os.getcwd()
  os.chdir(args.d)
  craftr.ext.install()

  with craftr.magic.enter_context(session, craftr.Session()):
    session.path.append(old_path)
    module = importlib.import_module('craftr.ext.' + args.m)

    try:
      targets = [session.targets[x] for x in args.targets]
    except KeyError as key:
      print('error: Target "{0}" does not exist'.format(key))
      return errno.ENOENT

    if args.e:
      with open('build.ninja', 'w') as fp:
        craftr.ninja.export(fp)

    if args.c == 1:
      files = set()
      for target in (targets or session.targets.values()):
        for fn in target.outputs:
          if os.path.isfile(fn):
            files.add(craftr.path.normpath(fn))
      print('cleaning {0} files...'.format(len(files)))
      for fn in files:
        try:
          os.remove(fn)
        except OSError:
          print('  error: could not remove "{0}"'.format(fn))
    elif args.c > 2:
      cmd = ['ninja', '-t', 'clean'] + [t.fullname for t in targets]
      ret = subprocess.call(cmd, shell=True)
      if ret != 0:
        return ret

    # Execute the build.
    if args.b:
      cmd = ['ninja'] + [t.fullname for t in targets]
      return subprocess.call(cmd, shell=True)

    return 0


if __name__ == '__main__':
  main()

# Copyright (C) 2015 Niklas Rosenstein
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

from craftr import utils, runtime
import craftr
import argparse
import os
import sys


def parse_args():
  parser = argparse.ArgumentParser(prog='craftr', description='Python based '
    'software meta build system.')
  parser.add_argument('targets', default=[], nargs='*', help='Zero or more '
    'target names. Relative identifiers will be resolved in the active '
    'modules namespace.')
  parser.add_argument('-c', '--clean', action='store_true', help='Clean '
    'the output files of the specified targets (or the output files of '
    'all targets if no target was specified).')
  parser.add_argument('-o', '--outfile', help='The name of the output file. '
    'Omit to use the default output file of the backend.')
  parser.add_argument('-m', '--module', help='Name of the main Craftr module '
    'to use for this session. If not specified, the `Craftr` file from the '
    'current directory is used.')
  parser.add_argument('-b', '--backend', default='ninja', help='The backend '
    'that will perform the export of the build rules. Currently supports '
    'only ninja. Use the "null" backend to do a dry run.')
  parser.add_argument('-v', '--verbose', action='store_true', help='Show '
    'debug output.')
  parser.add_argument('-f', '--func', default=[], action='append',
    help='The name of functions to be run after the export.')
  parser.add_argument('-D', default=[], action='append', help='Define '
    'options on the command-line before modules are being executed.')
  return parser.parse_args()


def main():
  args = parse_args()
  session = runtime.Session(args.backend, args.outfile)
  session.logger.level = 0 if args.verbose else craftr.logging.INFO

  # Use the local "Craftr" file if no module was specified.
  if not args.module:
    if not os.path.isfile('Craftr'):
      session.error('`Craftr` file does not exist.')
    args.module = runtime.Module(session, 'Craftr').read_identifier()

  # Set the any options.
  for item in args.D:
    key, eq, value = item.partition('=')
    if not utils.validate_ident(key):
      session.error("invalid identifier '{}'".format(key))

    if not eq:
      value = True
    elif not value:
      value = ''
    elif value.lower() == 'true':
      value = True
    elif value.lower() == 'false':
      value = False
    else:
      try:
        value = int(value)
      except ValueError:
        pass

    key = utils.abs_ident(key, args.module)
    modname, name = utils.split_ident(key)
    mod = session.get_namespace(modname)
    setattr(mod, name, value)

  # Load the module.
  try:
    module = session.load_module(args.module)
  except runtime.NoSuchModule as exc:
    session.error(exc)
  except runtime.ModuleError as exc:
    session.logger.debug(
      "error in module '{}', abort".format(exc.origin.identifier))
    sys.exit(exc.code)

  # Resolve the target names.
  targets = []
  for target in args.targets:
    if not utils.validate_ident(target):
      session.error("invalid target identifier '{}'".format(target))
    target = utils.abs_ident(target, module.identifier)
    modname, target = utils.split_ident(target)
    try:
      mod = session.get_module(modname)
    except runtime.NoSuchModule as exc:
      session.error("no module '{}'".format(exc.name))
    if target not in mod.targets:
      session.error("no target '{}' in '{}'".format(parts[0], modname))
    targets.append(mod.targets[target])

  if args.clean:
    files = []
    if not targets:
      for module in session.modules.values():
        for target in module.targets.values():
          files.extend(target.outputs)
    else:
      for target in targets:
        files.extend(target.outputs)
    session.info('Cleaning {} files ...'.format(len(files)))
    for filename in files:
      if os.path.isfile(filename):
        try:
          os.remove(filename)
        except OSError as exc:
          session.warn('"{}": {}'.format(filename, exc))
      elif os.path.exists(filename):
        session.warn('"{}": can not be removed (not a file)'.format(filename))

  functions = []
  for name in args.func:
    name = utils.abs_ident(name, module.identifier)
    modname, name = utils.split_ident(name)
    try:
      mod = session.get_module(modname)
    except runtime.NoSuchModule as exc:
      session.error("no module '{}'".format(exc.name))

    try:
      func = getattr(module.locals, name)
    except AttributeError:
      session.error("no member '{}' in module '{}'".format(name, modname))
    if not callable(func):
      session.error("'{}.{}' is not callable".format(modname, name))
    functions.append(func)

  # Do we even have any targets that could be exported?
  has_target = False
  for module in session.modules.values():
    if module.targets:
      has_target = True
      break

  if session.outfile and has_target:
    session.info('exporting to "{}"...'.format(session.outfile))
    with open(session.outfile, 'w') as fp:
      session.backend.export(fp, session, targets)

  for func in functions:
    func()


if __name__ == '__main__':
  main()

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

import craftr.utils, craftr.runtime, craftr.backend
import argparse
import os
import traceback
import sys


def parse_args():
  parser = argparse.ArgumentParser(
    prog='craftr',
    description='Python based software meta build system.')
  parser.add_argument(
    '-v', '--verbose',
    action='store_true',
    help='Enable verbose output.')
  parser.add_argument(
    '--version',
    action='store_true',
    help='Output the Craftr version and exit, regardless of other arguments.')
  parser.add_argument(
    '-c', '--cdir',
    help='The directory from which the "Craftfile" will be used as the '
      'main Craftr module if the -m/--module option is not specified. '
      'Defaults to the current working directry.')
  parser.add_argument(
    '-m', '--module',
    help='The name of the main Craftr module. If omitted, the "Craftfile" '
      'from the current working directory is used.')
  parser.add_argument(
    '-D', '--define',
    dest='defines',
    default=[],
    action='append',
    help='Pre-define options on the command-line before the Craftr modules '
      'are being loaded. Relative identifiers are automatically directed '
      'into the main Craftr module. To set a global variable, use '
      '"-Dglobals.<key>" or "-D:<key>". The value is converted to the best '
      'matching datatype. (Just the key name will result it to be set to '
      'True, booleans and integers are automatically converted and any other '
      'value is used as a string as-is).')
  sub_parsers = parser.add_subparsers(dest='cmd')

  run_parser = sub_parsers.add_parser(
    'run',
    help='Call one or more Python functions from a Craftr module.')
  run_parser.add_argument(
    'tasks',
    nargs='+',
    help='One or more names of Python functions. Relative names will be '
      'resolved in the main Craftr module specified via the -m/--module '
      'option or the "Craftfile" file in the current directory.')

  export_parser = sub_parsers.add_parser(
    'export',
    help='Export build definitions.')
  export_parser.add_argument(
    'backend',
    nargs='?',
    default='ninja',
    help='The backend of the export. Any additional arguments depend on '
      'the backend implementation. The backend is resolved into a Python '
      'module name that is either "craftr.backend.<name>" or '
      '"craftr_<name>_backend" and is then imported. See the "craftr.backend" '
      'module for additional information.')
  export_parser.add_argument(
    'backend_args',
    help='Additional arguments for the backend.',
    nargs='...')


  clean_parser = sub_parsers.add_parser(
    'clean',
    help='Remove the output files of the specified targets. Note that this '
      'command does not support recursive cleaning, it will only clean the '
      'direct outputs of the specified targets.')
  clean_parser.add_argument(
    'targets',
    nargs='*',
    help='The name of the targets. If none are specified, cleans all '
      'output files.')

  return parser.parse_args()


def main_export(args, session, module):
  try:
    backend = craftr.backend.load_backend(args.backend)
  except ValueError as exc:
    session.error('no backend "{}"'.format(args.backend))

  # Hook up the arguments to the backend and let it parse the arguments.
  old_argv = sys.argv
  sys.argv = ['creator export ' + craftr.utils.shell.quote(args.backend)]
  sys.argv.extend(args.backend_args)
  try:
    backend_args = backend.parse_args()
  finally:
    sys.argv = old_argv

  backend.main(backend_args, session, module)


def main_run(args, session, module):
  # Collect a list of all Python objects to call.
  tasks = []
  for name in args.tasks:
    name = craftr.utils.abs_ident(name, module.identifier)
    modname, name = craftr.utils.split_ident(name)
    mod = session.get_module(modname)

    try:
      func = getattr(module.locals, name)
    except AttributeError:
      session.error('"{}.{}" does not exist'.format(modname, name))
    if not callable(func):
      session.error('"{}.{}" is not callable'.format(modname, name))
    tasks.append(func)

  [task() for task in tasks]


def main_clean(args, session, module):
  # Collect a list of the files to be cleaned.
  files = []
  if not args.targets:
    for module in session.modules.values():
      for target in module.targets.values():
        files.extend(target.outputs)
  else:
    for target in args.targets:
      target = session.resolve_target(target, module)
      files.extend(target.outputs)

  session.info('cleaning {} files ...'.format(len(files)))
  for filename in files:
    if os.path.isfile(filename):
      try:
        os.remove(filename)
      except OSError as exc:
        session.warn('"{}": {}'.format(filename, exc))
    elif os.path.exists(filename):
      session.warn('"{}": can not be removed (not a file)'.format(filename))


def main():
  args = parse_args()
  if args.version:
    print('Craftr version', craftr.__version__)
    print('https://github.com/craftr-build/craftr')
    return

  session = craftr.runtime.Session()
  if args.verbose:
    session.logger.level = 0
  else:
    session.logger.level = craftr.logging.INFO

  # Use the local Craftfile if no explicit module was specified.
  if not args.module:
    filename = 'Craftfile'
    if args.cdir:
      filename = os.path.join(args.cdir, filename)
    if not os.path.isfile(filename):
      session.error('"{}" does not exist.'.format(filename))
    args.module = craftr.runtime.Module(session, filename).read_identifier()

  # Process and update the pre-definitions.
  for item in args.defines:
    key, eq, value = item.partition('=')
    if key.startswith(':'):
      key = 'globals.' + key[1:]
    if not craftr.utils.validate_ident(key):
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

    key = craftr.utils.abs_ident(key, args.module)
    modname, name = craftr.utils.split_ident(key)
    mod = session.get_namespace(modname)
    setattr(mod, name, value)
    session.logger.debug('setting {}.{} = {!r}'.format(modname, name, value))

  # Load the module.
  try:
    module = session.load_module(args.module)
    if not args.cmd:
      return
    # Dispatch the sub command procedure.
    globals()['main_' + args.cmd](args, session, module)
  except craftr.runtime.NoSuchModule as exc:
    session.logger.debug(traceback.format_exc())
    session.error('module "{0}" could not be found'.format(exc.name))
  except craftr.runtime.ModuleError as exc:
    session.logger.debug(traceback.format_exc())
    sys.exit(exc.code)
  except Exception as exc:
    session.error(traceback.format_exc())
    sys.exit(getattr(exc, 'code', 1))


if __name__ == '__main__':
  main()

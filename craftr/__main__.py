# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import craftr.runtime
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
  return parser.parse_args()


def main():
  args = parse_args()
  session = craftr.runtime.Session(args.backend, args.outfile)
  session.logger.level = 0 if args.verbose else craftr.logging.INFO

  # Determine the module to load.
  try:
    if not args.module:
      if not os.path.isfile('Craftr'):
        session.error('`Craftr` file does not exist.')
      module = session.load_module_file('Craftr')
      args.module = module.identifier
    else:
      try:
        module = session.load_module(args.module)
      except craftr.runtime.NoSuchModule as exc:
        session.error(exc)
  except craftr.runtime.ModuleError as exc:
    session.logger.debug(
      "error in module '{}', abort".format(exc.origin.identifier))
    sys.exit(exc.code)

  # Resolve the target names.
  targets = []
  for target in args.targets:
    if not craftr.utils.validate_ident(target):
      session.error("invalid target identifier '{}'".format(target))
    target = craftr.utils.abs_ident(target, module.identifier)
    modname, target = craftr.utils.split_ident(target)
    try:
      mod = session.get_module(modname)
    except craftr.runtime.NoSuchModule as exc:
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
    name = craftr.utils.abs_ident(name, module.identifier)
    modname, name = craftr.utils.split_ident(name)
    try:
      mod = session.get_module(modname)
    except craftr.runtime.NoSuchModule as exc:
      session.error("no module '{}'".format(exc.name))

    try:
      func = getattr(module.locals, name)
    except AttributeError:
      session.error("no member '{}' in module '{}'".format(name, modname))
    if not callable(func):
      session.error("'{}.{}' is not callable".format(modname, name))
    functions.append(func)

  if session.outfile:
    session.info('exporting to "{}"...'.format(session.outfile))
    with open(session.outfile, 'w') as fp:
      session.backend.export(fp, session, targets)

  for func in functions:
    func()

if __name__ == '__main__':
  main()

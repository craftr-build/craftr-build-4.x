# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import craftr.runtime
import argparse
import os
import sys


def parse_args():
  parser = argparse.ArgumentParser(prog='craftr', description='Python based '
    'software meta build system.')
  parser.add_argument('targets', default=[], nargs='*', help='The name of '
    'the targets to export as phony targets or to clean non-recursively.')
  parser.add_argument('-c', '--clean', action='store_true', help='Clean '
    'the output files of the specified targets (or the output files of '
    'all targets if no target was specified).')
  parser.add_argument('-d', '--dry', action='store_true', help='Dry run. Do '
    'not invoke the backend exporter.')
  parser.add_argument('-o', '--outfile', help='The name of the output file. '
    'Omit to use the default output file of the backend.')
  parser.add_argument('-m', '--module', help='Name of the main Craftr module '
    'to use for this session. If not specified, the `Craftr` file from the '
    'current directory is used.')
  parser.add_argument('-b', '--backend', default='ninja', help='The backend '
    'that will perform the export of the build rules. Currently supports '
    'only ninja.')
  return parser.parse_args()


def main():
  args = parse_args()
  session = craftr.runtime.Session()
  logger = session.logger
  backend = craftr.backend.load_backend(args.backend)

  # Determine the module to load.
  try:
    if not args.module:
      if not os.path.isfile('Craftr'):
        logger.error('`Craftr` file does not exist.')
        return 1
      module = session.load_module_file('Craftr')
      args.module = module.identifier
    else:
      try:
        module = session.load_module(args.module)
      except craftr.runtime.NoSuchModule as exc:
        logger.error(exc)
        return 1
  except craftr.runtime.ModuleError as exc:
    logger.debug("error in module '{0}', abort".format(exc.origin.identifier))
    sys.exit(exc.code)

  # Resolve the target names.
  targets = []
  for target in args.targets:
    if not craftr.runtime.validate_identifier(target):
      logger.error("invalid target identifier '{0}'".format(target))
    parts = target.split('.')
    modname = '.'.join(parts[:-1])
    target = parts[-1]
    if not modname:
      modname = module.identifier
    try:
      mod = session.get_module(modname)
    except craftr.runtime.NoSuchModule as exc:
      logger.error("no module '{0}'".format(exc.name))
      return 1
    if target not in mod.targets:
      logger.error("no target '{0}' in '{1}'".format(parts[0], modname))
      return 1
    targets.append(mod.targets[target])

  if args.clean:
    if not targets:
      targets = []
      for module in session.modules.values():
        targets.extend(module.targets.values())
    files = []
    for target in targets:
      files.extend(target.outputs)
    logger.info('Cleaning {0} files ...'.format(len(files)))
    for filename in files:
      if os.path.isfile(filename):
        try:
          os.remove(filename)
        except OSError as exc:
          logger.warn('"{0}": {1}'.format(filename, exc))
      elif os.path.exists(filename):
        logger.warn('"{0}": can not be removed (not a file)'.format(filename))

  if args.dry:
    logger.debug('dry run, no export. abort')
    return

  if not args.outfile:
    args.outfile = backend.default_outfile

  logger.info('exporting to "{0}"...'.format(args.outfile))
  with open(args.outfile, 'w') as fp:
    backend.export(fp, session, targets)


if __name__ == '__main__':
  main()

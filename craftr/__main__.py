# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import craftr.runtime
import argparse
import os
import sys


def parse_args():
  parser = argparse.ArgumentParser(prog='craftr', description='Python based '
    'software meta build system.')
  parser.add_argument('-m', '--module', help='Name of the main Craftr module '
    'to use for this session. If not specified, the `Craftr` file from the '
    'current directory is used.')
  parser.add_argument('-f', '--format', choices=['ninja'], help='The output '
    'format of the meta build session. Currently only supports Ninja.')
  return parser.parse_args()


def main():
  args = parse_args()
  session = craftr.runtime.Session()

  # Determine the module to load.
  try:
    if not args.module:
      if not os.path.isfile('Craftr'):
        session.logger.error('`Craftr` file does not exist.')
        return 1
      module = session.load_module_file('Craftr')
      args.module = module.identifier
    else:
      try:
        module = session.load_module(args.module)
      except craftr.runtime.NoSuchModule as exc:
        session.logger.error(exc)
        return 1
  except craftr.runtime.ModuleError as exc:
    session.logger.debug("error in module '{0}', abort".format(
      exc.origin.identifier))
    sys.exit(exc.code)

if __name__ == '__main__':
  main()

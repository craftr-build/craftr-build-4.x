# The Craftr build system
# Copyright (C) 2016  Niklas Rosenstein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from craftr.core.logging import logger
from craftr.core.session import session, Session, Module
from craftr.utils import path
from nr.types.version import Version

import abc
import argparse
import atexit
import json
import sys
import textwrap


class BaseCommand(object, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def build_parser(self, parser):
    pass

  @abc.abstractmethod
  def execute(self, parser, args):
    pass


class run(BaseCommand):

  def build_parser(self, parser):
    parser.add_argument('module', nargs='?')
    parser.add_argument('version', nargs='?', default='*')

  def execute(self, parser, args):
    if not args.module:
      for fn in ['manifest.json', 'craftr/manifest.json']:
        if path.isfile(fn):
          module = session.parse_manifest(fn)
          break
      else:
        parser.error('no Craftr package "manifest.json" found')
    else:
      try:
        module = session.find_module(args.module, args.version)
      except Module.NotFound as exc:
        parser.error('module not found: ' + str(exc))
    module.run()


class startproject(BaseCommand):

  def build_parser(self, parser):
    parser.add_argument('name')
    parser.add_argument('directory', nargs='?', default=None)
    parser.add_argument('--version', type=Version, default='1.0.0')
    parser.add_argument('--plain', action='store_true')

  def execute(self, parser, args):
    directory = args.directory or args.name
    if not args.plain:
      directory = path.join(directory, 'craftr')

    if not path.exists(directory):
      logger.debug('creating directory "{}"'.format(directory))
      path.makedirs(directory)
    elif not path.isdir(directory):
      logger.error('"{}" is not a directory'.format(directory))
      return 1

    mfile = path.join(directory, 'manifest.json')
    sfile = path.join(directory, 'Craftrfile')
    for fn in [mfile, sfile]:
      if path.isfile(fn):
        logger.error('"{}" already exists'.format(fn))
        return 1

    logger.debug('creating file "{}"'.format(mfile))
    with open(mfile, 'w') as fp:
      fp.write(textwrap.dedent('''
        {
          "name": "%s",
          "version": "%s",
          "author": "",
          "url": "",
          "dependencies": {},
          "options": {},
          "loaders": []
        }\n''' % (args.name, args.version)).lstrip())

    logger.debug('creating file "{}"'.format(sfile))
    with open(sfile, 'w') as fp:
      print('# {}'.format(args.name), file=fp)


def main():
  parser = argparse.ArgumentParser(prog='craftr', description='The Craftr build system')
  parser.add_argument('-v', dest='verbose', action='count', default=0)
  subparsers = parser.add_subparsers(dest='command')

  commands = {}
  for class_ in BaseCommand.__subclasses__():
    cmd = class_()
    cmd.build_parser(subparsers.add_parser(class_.__name__))
    commands[class_.__name__] = cmd

  args = parser.parse_args()
  Session.start()
  atexit.register(Session.end)

  if not args.command:
    parser.print_usage()
    return 0

  return commands[args.command].execute(parser, args)


if __name__ == '__main__':
  sys.exit(main())

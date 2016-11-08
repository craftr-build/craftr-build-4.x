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

from craftr.core.session import session, Session

import abc
import argparse
import atexit
import sys


class BaseCommand(object, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def build_parser(self, root_parser, subparsers):
    pass

  @abc.abstractmethod
  def execute(self, parser, args):
    pass


class run(BaseCommand):

  def build_parser(self, root_parser, subparsers):
    parser = subparsers.add_parser('run')
    parser.add_argument('module', nargs='?')
    parser.add_argument('version', nargs='?', default='*')

  def execute(self, parser, args):
    if not args.module:
      # TODO: Determine module in CWD and load that.
      parser.error("no module name specified")
    module = session.find_module(args.module, args.version)
    module.run()


def main():
  parser = argparse.ArgumentParser(prog='craftr', description='The Craftr build system')
  parser.add_argument('-v', action='count', default=0)
  subparsers = parser.add_subparsers(dest='command')

  commands = {}
  for class_ in BaseCommand.__subclasses__():
    cmd = commands[class_.__name__] = class_()
    cmd.build_parser(parser, subparsers)

  args = parser.parse_args()
  Session.start()
  atexit.register(Session.end)

  if not args.command:
    parser.print_usage()
    return 0

  commands[args.command].execute(parser, args)


if __name__ == '__main__':
  sys.exit(main())

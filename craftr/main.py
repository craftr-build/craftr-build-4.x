
import argparse
import os
import sys

from . import dsl


class Context(dsl.Context):

  def __init__(self):
    self.options = {}

  def get_option(self, module_name, option_name):
    return self.options[module_name + '.' + option_name]


def get_argument_parser():
  parser = argparse.ArgumentParser(prog='craftr')
  parser.add_argument('-f', '--file', default='build.craftr', help='The Craftr build script to execute.')
  return parser


def _main(argv=None):
  parser = get_argument_parser()
  args = parser.parse_args(argv)

  context = Context()
  context.options['myproject.foo'] = '32'
  with open(args.file) as fp:
    project = dsl.Parser().parse(fp.read())
  module = dsl.Interpreter(context, args.file)(project)
  return 0


def main():
  sys.exit(_main())

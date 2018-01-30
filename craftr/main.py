
import argparse
import os
import sys

from . import builtins, dsl


class Context(dsl.Context):

  def __init__(self):
    self.path = ['.', os.path.join(os.path.dirname(__file__), 'lib')]
    self.options = {}
    self.modules = {}

  def get_option(self, module_name, option_name):
    return self.options[module_name + '.' + option_name]

  def get_module(self, module_name):
    if module_name not in self.modules:
      for path in self.path:
        filename = os.path.join(path, module_name + '.craftr')
        if os.path.isfile(filename):
          break
        filename = os.path.join(path, module_name, 'build.craftr')
        if os.path.isfile(filename):
          break
      else:
        raise dsl.ModuleNotFoundError(module_name)
      with open(filename) as fp:
        project = dsl.Parser().parse(fp.read())
      module = dsl.Interpreter(self, filename)(project)
      self.modules[module_name] = module
    return module

  def init_module(self, module):
    super().init_module(module)
    ns = module.eval_namespace()
    for key in builtins.__all__:
      setattr(ns, key, getattr(builtins, key))


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

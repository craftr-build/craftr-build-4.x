
import argparse
import os
import sys

from . import builtins, dsl


class Context(dsl.Context):

  def __init__(self, build_mode='debug'):
    self.path = ['.', os.path.join(os.path.dirname(__file__), 'lib')]
    self.options = {}
    self.modules = {}
    self.build_mode = build_mode

  def option_default(self, name, value):
    return self.options.setdefault(name, value)

  def translate_targets(self, module):
    seen = set()
    def translate(target):
      for dep in target.dependencies():
        if dep.target():
          translate(dep.target())
        else:
          for target in dep.module().targets():
            translate(target)
      if target not in seen:
        seen.add(target)
        for handler in target.target_handlers():
          handler.translate_target(target)
    for target in module.targets():
      translate(target)

  # dsl.Context

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
    ns.BUILD = builtins.BuildInfo(self.build_mode)
    ns.option_default = self.option_default


def get_argument_parser():
  parser = argparse.ArgumentParser(prog='craftr')
  parser.add_argument('-f', '--file', default='build.craftr', help='The Craftr build script to execute.')
  parser.add_argument('--debug', action='store_true', help='Produce a debug build (default).')
  parser.add_argument('--release', action='store_true', help='Produce a release build.')
  return parser


def _main(argv=None):
  parser = get_argument_parser()
  args = parser.parse_args(argv)

  # Validate options.
  if args.debug and args.release:
    parser.error('--debug and --release are incompatible options.')

  # Create the build context.
  context = Context(build_mode='release' if args.release else 'debug')

  # Load the main build script.
  with open(args.file) as fp:
    project = dsl.Parser().parse(fp.read())
  module = dsl.Interpreter(context, args.file)(project)

  # Translate targets.
  context.translate_targets(module)

  # TODO: Export step
  # TODO: Build step

  return 0


def main():
  sys.exit(_main())

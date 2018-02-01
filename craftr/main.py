
import argparse
import os
import sys

from . import builtins, dsl


class Context(dsl.BaseDslContext):

  def __init__(self, build_directory, build_mode='debug'):
    self.path = ['.', os.path.join(os.path.dirname(__file__), 'lib')]
    self.options = {}
    self.modules = {}
    self.build_directory = build_directory
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
          handler.translate_target(target, target.handler_data(handler))
    for target in module.targets():
      translate(target)

  def load_module_file(self, filename):
    with open(filename) as fp:
      project = dsl.Parser().parse(fp.read())
    return dsl.Interpreter(self, filename)(project)

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
    else:
      module = self.modules[module_name]
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
  parser.add_argument('-f', '--file', default='build.craftr', help='The Craftr build script to execute. Onlt with --configure. Can be omitted when the configure step was peformed once and then --reconfigure is used.')
  parser.add_argument('-c', '--configure', action='store_true', help='Enable the configure step. This causes the build scripts to be executed and the files for the build step to be generated.')
  parser.add_argument('-r', action='store_true', help='Enable re-configuration, only with -c, --configure.')
  parser.add_argument('--reconfigure', action='store_true', help='Enable re-configureation, inheriting all options from the previous configure step. Implies --configure.')
  parser.add_argument('-D', '--debug', action='store_true', help='Produce a debug build (default if --reconfigure is NOT used).')
  parser.add_argument('-R', '--release', action='store_true', help='Produce a release build.')
  parser.add_argument('-o', '--options', nargs='+', metavar='OPTION', help='Specify one or more options in the form of [<project>].<option>[=<value>]. Successive options may omitt the [<project>] part.')
  parser.add_argument('--backend', help='The build backend to use. This option can only be used during the configure step.')
  parser.add_argument('--backend-args', action='append', metavar='ARGS', help='A string with additional command-line arguments for the build backend. Can be used multiple times. Only with --clean and/or --build.')
  parser.add_argument('--clean', action='store_true', help='Enable the clean step. This step is always executed after the configure step and before the build step, if either are enabled.')
  parser.add_argument('-b', '--build', action='store_true', help='Enable the build step. This step is always executed after the configure step, if it is also enabled.')
  parser.add_argument('targets', nargs='*', metavar='TARGET', help='Zero or more targets to clean and/or build. If neither --clean nor --build is used, passing targets will cause an error.')
  return parser


def _main(argv=None):
  parser = get_argument_parser()
  args = parser.parse_args(argv)

  if args.r and not args.configure:
    parser.error('-r: use --reconfigure or combine with -c, --configure')
  if args.debug and args.release:
    parser.error('--debug: can not be combined with --release')
  if (not args.clean or not args.build) and args.targets:
    parser.error('TARGET: can only be specified with --clean and/or --build')
  if (not args.clean or not args.build) and args.backend_args:
    parser.error('--backend-args: can only be specified with --clean and/or --build')
  if not (args.configure or args.reconfigure) and args.file:
    parser.error('--file: can only be specified with --configure or --reconfigure')

  # Turn a directory-like file or one that actually points to a directory
  # point to the directories' build.craftr file instead.
  if args.file.endswith('/') or args.file.endswith('\\') or \
      os.path.isdir(args.file):
    args.file = os.path.join(args.file, 'build.craftr')

  # Load the build script.
  mode = 'release' if args.release else 'debug'
  build_directory = os.path.join('build', mode)
  context = Context(build_directory, mode)
  module = context.load_module_file(args.file)

  # Translate targets.
  context.translate_targets(module)

  # TODO: Export step
  # TODO: Build step

  return 0


def main():
  sys.exit(_main())

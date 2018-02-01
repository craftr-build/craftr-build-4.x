
import argparse
import json
import os
import sys

from . import dsl, path, props
from .context import Context


def set_options(context, options):
  prev_scope = None
  for item in options:
    name, assign, value = item.partition('=')
    scope, name = name.rpartition('.')[::2]
    if not scope: scope = prev_scope
    if not scope or not name:
      parser.error('--options: invalid argument: {}'.format(item))
    if not assign:
      value = 'true'
    if assign and not value:
      # TODO: Unset the option.
      context.options.pop('{}.{}'.format(scope, name))
    else:
      context.options['{}.{}'.format(scope, name)] = value
    prev_scope = scope


def get_argument_parser():
  parser = argparse.ArgumentParser(prog='craftr')
  parser.add_argument('--build-root', default='build', help='The build root directory. Defaults to build/')
  parser.add_argument('-f', '--file', default=None, help='The Craftr build script to execute. Onlt with --configure. Can be omitted when the configure step was peformed once and then --reconfigure is used.')
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
  if not (args.clean or args.build) and args.targets:
    parser.error('TARGET: can only be specified with --clean and/or --build')
  if not (args.clean or args.build) and args.backend_args:
    parser.error('--backend-args: can only be specified with --clean and/or --build')
  if not (args.configure or args.reconfigure) and args.file:
    parser.error('--file: can only be specified with --configure or --reconfigure')
  if not (args.configure or args.reconfigure) and args.backend:
    parser.error('--backend: can only be specified with --configure or --reconfigure')
  if not (args.configure or args.reconfigure or args.clean or args.build):
    parser.print_usage()
    return 0

  # Assign flag implications.
  if args.r:
    args.configure = True
    args.reconfigure = True
  if args.reconfigure:
    args.configure = True
  if not args.options:
    args.options = []

  # Load the cache file from the build root directory, if it exists.
  root_cachefile = path.join(args.build_root, 'CraftrBuildRoot.json')
  if os.path.isfile(root_cachefile):
    with open(root_cachefile) as fp:
      try:
        root_cache = json.load(fp)
      except json.JSONDecodeError as exc:
        print('warning: {} is can not be loaded ({})'.format(
          root_cachefile, exc))
        root_cache = {}
  else:
    root_cache = {}

  # In a reconfiguration, we want to inherit the build mode, build file
  # and command-line options, if not already specified.
  if args.reconfigure:
    inherited_flags = []
    if 'mode' in root_cache and not (args.debug or args.release):
      # Inherit --debug or --release.
      if root_cache['mode'] == 'debug':
        inherited_flags.append('--debug')
        args.debug = True
      elif root_cache['mode'] == 'release':
        inherited_flags.append('--release')
        args.release = True
    if root_cache.get('options'):
      inherited_flags.append('--options')
      inherited_flags += root_cache['options']
      args.options = root_cache['options'] + args.options
    if 'file' in root_cache and not args.file:
      args.file = root_cache['file']
      inherited_flags += ['--file', args.file]
    if inherited_flags:
      print('note: inherited', ' '.join(inherited_flags))

  if not (args.debug or args.release):
    args.debug = True
  mode = 'release' if args.release else 'debug'
  build_directory = os.path.join('build', mode)

  if args.configure:
    # TODO: Handle --reconfigure by reading previously define build
    #       mode and options.

    if not args.file:
      args.file = 'build.craftr'
    # Turn a directory-like file or one that actually points to a directory
    # point to the directories' build.craftr file instead.
    elif args.file.endswith('/') or args.file.endswith('\\') or \
        os.path.isdir(args.file):
      args.file = os.path.join(args.file, 'build.craftr')

    # Load the build script.
    context = Context(build_directory, mode, args.backend)
    set_options(context, args.options)
    module = context.load_module_file(args.file)
    context.translate_targets(module)
    context.serialize()

  elif (args.clean or args.build):
    context = Context(build_directory, None)
    context.deserialize()
    set_options(context, args.options)

  # Load the backend module.
  backend_module = context.get_module(context.backend_name)
  backend_factory = backend_module.eval_namespace().new_backend
  backend_args = []
  for x in (args.backend_args or ()):
    backend_args += x
  backend = backend_factory(context, module, backend_args)

  if args.configure:
    # Write the root cache back.
    root_cache['main'] = module.name()
    root_cache['mode'] = 'debug' if args.debug else 'release'
    root_cache['options'] = args.options
    root_cache['file'] = args.file
    path.makedirs(args.build_root)
    with open(path.join(args.build_root, 'CraftrBuildRoot.json'), 'w') as fp:
      json.dump(root_cache, fp)
    backend.export()

  for target in args.targets:
    if '/' not in target:
      target = root_cache['main'] + '/' + target
    context.build_graph.select(target)

  if args.clean:
    backend.clean()

  if args.build:
    # TODO: Build step
    res = backend.build()
    if res not in (0, None):
      return res

  return 0


def main():
  sys.exit(_main())

# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
"""
Implements the Craftr command-line interface.
"""

from . import dsl
from nr import path

import argparse
import collections
import json
import os
import sys


class Context(dsl.Context):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.backend_name = 'backends.ninja'
    self.cache = {}

  def to_json(self):
    root = collections.OrderedDict()
    root['path'] = self.path
    root['backend'] = self.backend_name
    root['variant'] = self.build_variant
    root['directory'] = self.build_directory
    root['options'] = None  # TODO: Include options specified via the command-line.
    root['graph'] = self.graph.to_json()
    root['cache'] = self.cache
    return root

  def from_json(self, root):
    self.path = root['path']
    self.backend_name = root['backend']
    self.build_variant = root['variant']
    if self.build_directory != root['directory']:
      print('warning: stored build directory does not match current build directory')
    # TODO: Read options
    self.graph.from_json(root['graph'])
    self.cache.update(root.get('cache', {}))

  def serialize(self):
    path.makedirs(self.build_directory)
    with open(path.join(self.build_directory, 'CraftrBuildGraph.json'), 'w') as fp:
      json.dump(self.to_json(), fp)

  def deserialize(self):
    with open(path.join(self.build_directory, 'CraftrBuildGraph.json')) as fp:
      root = json.load(fp, object_pairs_hook=collections.OrderedDict)
    self.from_json(root)


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
  parser.add_argument('--recursive', action='store_true', help='Enable recursive target cleanup. Only with --clean')
  parser.add_argument('-b', '--build', action='store_true', help='Enable the build step. This step is always executed after the configure step, if it is also enabled.')
  parser.add_argument('--show', metavar='ACTION', help='Shows the specified action.')
  parser.add_argument('--show-actions', action='store_true', help='Shows a list of available build actions.')
  parser.add_argument('targets', nargs='...', metavar='TARGET', help='Zero or more targets/actions to clean and/or build. If neither --clean nor --build is used, passing targets will cause an error.')
  parser.add_argument('-t', '--tool', nargs='...', help='Run a tool with the specified arguments.')
  return parser


def main(argv=None):
  parser = get_argument_parser()
  args = parser.parse_args(argv)
  has_buildsteps = (args.configure or args.reconfigure or args.r or args.clean or args.build)
  metaopts = ['tool', 'show', 'show-actions']
  active_metaopts = []

  if args.r and not args.configure:
    parser.error('-r: use --reconfigure or combine with -c, --configure')
  if args.debug and args.release:
    parser.error('--debug: can not be combined with --release')
  if not (args.clean or args.build) and args.targets:
    if args.tool:
      args.tool += args.targets
    else:
      parser.error('TARGET: can only be specified with --clean and/or --build')
  if not (args.clean or args.build) and args.backend_args:
    parser.error('--backend-args: can only be specified with --clean and/or --build')
  if not (args.configure or args.reconfigure) and args.file:
    parser.error('--file: can only be specified with --configure or --reconfigure')
  if not (args.configure or args.reconfigure) and args.backend:
    parser.error('--backend: can only be specified with --configure or --reconfigure')
  if args.recursive and not args.clean:
    parser.error('--recursive: can only be specified with --clean')
  if args.tool is not None and len(args.tool) < 1:
    parser.error('--tool: need at least one argument (tool name)')
  for opt in metaopts:
    active = getattr(args, opt.replace('-', '_'))
    if active and has_buildsteps:
      parser.error('--{}: can not be combined with Craftr build steps'.format(opt))
    if active:
      active_metaopts.append(opt)
  if len(active_metaopts) >= 2:
    parser.error('can not combined these options: {}'.format(', '.join('--' + x for x in active_metaopts)))
  if not has_buildsteps and not active_metaopts:
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

  # Handle --tool.
  if args.tool:
    context = Context(None, None)
    set_options(context, args.options)
    sys.argv = ['craftr -t ' + args.tool[0]] + sys.argv[1:]
    try:
      module = context.get_module(args.tool[0])
    except dsl.ModuleNotFoundError as exc:
      try:
        module = context.get_module('tools.' + args.tool[0])
      except dsl.ModuleNotFoundError:
        raise exc
    scope = context.get_exec_vars(module)
    scope['main'](args.tool[1:])
    return

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
  build_variant = 'release' if args.release else 'debug'
  build_directory = os.path.join('build', build_variant)

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
    context = Context(build_variant, build_directory)
    set_options(context, args.options)
    module = context.load_file(args.file, is_main=True)
    context.translate_targets()
    context.serialize()

  else:
    context = Context(build_variant, build_directory)
    context.deserialize()
    set_options(context, args.options)

  # Handle --show.
  if args.show:
    if '@' not in args.show:
      args.show = root_cache['main'] + '@' + args.show
    action = context.graph[args.show]
    data = action.to_json()
    data['hash'] = context.graph.hash(action)
    print(json.dumps(data, sort_keys=True, indent=2))
    return 0
  # Handle --show-actions.
  if args.show_actions:
    for action in context.graph:
      print(action)
    return 0

  # Load the backend module.
  backend_module = context.load_module(context.backend_name)
  backend_factory = context.get_exec_vars(backend_module)['new_backend']
  backend_args = []
  for x in (args.backend_args or ()):
    backend_args += x
  backend = backend_factory(context, backend_args)

  if args.configure:
    # Write the root cache back.
    root_cache['main'] = module.name
    root_cache['mode'] = 'debug' if args.debug else 'release'
    root_cache['options'] = args.options
    root_cache['file'] = args.file
    path.makedirs(args.build_root)
    with open(path.join(args.build_root, 'CraftrBuildRoot.json'), 'w') as fp:
      json.dump(root_cache, fp)
    backend.export()

  for target in args.targets:
    if '@' not in target:
      target = root_cache['main'] + '@' + target
    context.graph.select(target)

  if args.clean:
    res = backend.clean(args.recursive)
    if res not in (0, None):
      return res

  if args.build:
    # TODO: Build step
    res = backend.build()
    if res not in (0, None):
      return res

  return 0


_entry_point = lambda: sys.exit(main())

"""
Command-line entry point for the Craftr build system.
"""

import argparse
import contextlib
import functools
import json
import os
import platform
import posixpath
import shlex
import shutil
import subprocess
import sys
import toml

import craftr from 'craftr'
import {concat} from 'craftr/utils/it'
import {plural, reindent, ReindentHelpFormatter} from 'craftr/utils/text'

error = functools.partial(print, file=sys.stderr)


parser = argparse.ArgumentParser(
  formatter_class=ReindentHelpFormatter,
  prog='craftr',
  description='''
    Craftr is a modular language-indepenent build system that is written in
    Python. It's core features are cross-platform compatibility, easy
    extensibility and Python as powerful build scripting language.
  ''',
)

parser.add_argument(
  '--quickstart',
  metavar='EXAMPLE',
  nargs='?',
  help='Copy one of the examples to the current working directory. Use '
       '--list-quickstart to show all available quickstart examples.'
)

parser.add_argument(
  '--list-quickstart',
  action='store_true',
  help='Show a list of all available quickstart examples and exit.'
)

parser.add_argument(
  '--list-tools',
  action='store_true',
  help='List tools available with the --tool option and exit.'
)

parser.add_argument(
  '-t', '--tool',
  metavar='NAME [ARGS ...]',
  nargs='...',
  help='Run a script from the craftr/tools directory.'
)

parser.add_argument(
  '--show-config-tags',
  action='store_true',
  help='Show the tags associated with the configuration and exit. They are '
       'the properties that you can use in the Craftr configuration file '
       'for conditional options.'
)

parser.add_argument(
  '--show-build-directory',
  action='store_true',
  help='Show the final build directory (including release and backend name) '
       'and exit.'
)

parser.add_argument(
  '--show-config',
  action='store_true',
  help='Print the configuration values in TOML format.'
)

parser.add_argument(
  '--recursive',
  action='store_true',
  help='Clean targets recursively in the --clean step.'
)

parser.add_argument(
  '--dry',
  action='store_true',
  help='In the --configure step, do not save any build configuration.'
)

parser.add_argument(
  '--release',
  action='store_true',
  help='Configure a release build. This option will set the `craftr.release` '
       'configuration value and also the `is_release` member of the Craftr '
       'core module.'
)

parser.add_argument(
  '--build-root',
  metavar='DIRECTORY',
  help='The build root directory. If not specified, defaults to the value '
       'of the `build.directory` option. If that is not specified, it '
       'defaults to build/ on --configure, otherwise it will be determined '
       'from the directories in the current working directory.'
)

parser.add_argument(
  '--build-directory',
  metavar='DIRECTORY',
  help='The build directory. If specified, overwrites what would be generated '
       'with --build-root. Defaults to <--build-root>/<debug/release>.'
)

parser.add_argument(
  '--cwd',
  metavar='DIRECTORY',
  help='Switch to the specified directory before executing. Note that any '
       'paths specified on the command-line will be relative to that '
       'directory.'
)

parser.add_argument(
  '--backend',
  help='The backend to use for building. The last (explicitly) used backend '
       'is remembered when using the --prepare-build or --build options. If '
       'this option is not defined, it is read from the `build.backend` '
       'configuration value. Defaults to `ninja`.'
)

parser.add_argument(
  '--save-cache',
  action='store_true',
  help='Save the cache (which includes the specified --options) to the build '
       'cache file. This option is implied by the --configure step.'
)

parser.add_argument(
  '--config',
  help='Specify a TOML configuration file to load. Note that any values '
       'specified with --options take precedence over the configuration '
       'file. Defaults to BUILD.cr.toml'
)

parser.add_argument(
  '--options',
  metavar='KEY=VALUE',
  nargs='+',
  default=[],
  action='append',
  help='Define one or more options that override the Craftr configuration '
       'file. This command-line option can be used multiple times.'
)

parser.add_argument(
  '--flush',
  action='store_true',
  help='Flush existing build configuration files. Use this option if you '
       'want to run the --configure step again without taking into options '
       'saved from a previous run.'
)

parser.add_argument(
  '-c', '--configure',
  metavar='BUILDSCRIPT',
  nargs='?',
  default=NotImplemented,
  help='Execute the build script and generate a JSON database file that '
       'contains all the build information.'
)

parser.add_argument(
  '--prepare-build',
  action='store_true',
  help='Prepare the build process by generating all files for the selected '
       'build backend, but not actually execute the build. Use this option if '
       'you want to invoke the build backend manually instead of via the '
       '--build step.'
)

parser.add_argument(
  '-b', '--build',
  metavar='TARGET',
  nargs='*',
  default=NotImplemented,
  help='Execute the build for all or the specified TARGETs using the build '
       'backend configured with --backend or in the Craftr configuration '
       'file. This step implies the --prepare-build step. Additional '
       'arguments can be passed to a target using the TARGET="ARGS ..." '
       'syntax (useful for run targets).'
)

parser.add_argument(
  '--run-node',
  metavar='NAME',
  help='Execute the command for the specified build-node. Build nodes names '
       'are formatted as `//<cell>:<target>#<node>`. This can be used '
       'internally by build backends to implement deduplication. This option '
       'requires the --build-directory to be set.'
)

parser.add_argument(
  '--show-node',
  metavar='NAME',
  help='Show the information for the specified build node.'
)

parser.add_argument(
  '--list-nodes',
  action='store_true',
  help='List all build nodes and exit.'
)

parser.add_argument(
  '--clean',
  metavar='TARGET',
  nargs='*',
  default=NotImplemented,
  help='Clean all or the specified TARGETs. Use the --recursive option if '
       'you want the specified targets to be cleaned recursively.'
)

parser.add_argument(
  '--dotviz',
  metavar='FILE',
  nargs='?',
  default=NotImplemented,
  help='Render a .dot graph file to the specified FILE or stdout and exit.'
)

parser.add_argument(
  '--build-args',
  action='append',
  default=[],
  help='Additional arguments for the --build step that are passed on to the '
       'build backend. The argument(s) to this option must be a string that '
       'will itself be treated as a list of arguments.'
)

parser.add_argument(
  '--clean-args',
  action='append',
  default=[],
  help='Additional arguments for the --clean step that are passed on to the '
       'build backend. The argument(s) to this option must be a string that '
       'will itself be treated as a list of arguments.'
)


def get_platform_tags():
  name = sys.platform.lower()
  system = platform.system().lower()
  tags = set()
  if name.startswith('win32'):
    if 'cygwin' in system:
      tags.add('cygwin')
    tags.add('win32')
  elif name.startswith('darwin'):
    tags.add('posix')
    tags.add('darwin')
  elif name.startswith('linux'):
    tags.add('posix')
    tags.add('linux')
    with open('/proc/version') as fp:
      if 'microsoft' in fp.read().lower():
        tags.add('wsl')
        tags.remove('linux')
  return tags


def mark_build_root(build_root):
  os.makedirs(build_root, exist_ok=True)
  open(os.path.join(build_root, '.craftr_build_root'), 'w').close()


def find_build_root():
  results = []
  for name in os.listdir('.'):
    if os.path.isfile(os.path.join(name, '.craftr_build_root')):
      results.append(name)
  if len(results) > 1:
    error('fatal: multiple candidates found for --build-root')
    error('       candidates are')
    for name in results:
      print('  --build-root', name)  # TODO shell quote
    sys.exit(1)
  if not results:
    return None
  return results[0]


def set_options(options):
  options = list(options)
  no_such_options = set()
  invalid_options = set()
  for option in options:
    key, sep, value = option.partition('=')
    if not sep:
      value = True
    elif not value:
      try:
        craftr.options.pop(key)
      except KeyError:
        no_such_options.add(key)
      continue
    else:
      if value.lower() in ('', 'true', '1', 'on', 'yes'):
        value = True
      elif value.lower() in ('false', '0', 'off', 'no'):
        value = False
    try:
      craftr.options[key] = value
    except KeyError:
      invalid_options.add(key)
  return no_such_options, invalid_options


def merge_options(*opts):
  result = []
  for option in concat(opts):
    key, sep, value = option.partition('=')
    for other in result:
      if other == key or other.startswith(key + '='):
        break
    else:
      result.append(option)
  return result


def get_additional_args_for(node_name):
  """
  In the --build step, a `craftr_additional_args.json` file may be present
  which specifies additional arguments passed to a target via the command-line.
  This extracts the additional arguments for the specified *node_name*, falling
  back to the node's target if such an entry exists.
  """

  additional_args_file = os.path.join(craftr.build_directory, 'craftr_additional_args.json')
  if not os.path.isfile(additional_args_file):
    return []
  with open(additional_args_file, 'r') as fp:
    additional_args = json.load(fp)
  try:
    return shlex.split(additional_args[node_name])
  except KeyError:
    pass
  target_name = node_name.partition('#')[0]
  try:
    return shlex.split(additional_args[target_name])
  except KeyError:
    pass
  return []


def run_build_node(graph, node_name):
  try:
    node = graph[node_name]
  except KeyError:
    error('fatal: build node "{}" does not exist'.format(node_name))
    return 1

  # TODO: The additional args feature should be explicitly supported by the
  #       build node, allowing it to specify a position where the additional
  #       args will be rendered.
  #       Usually, the option only makes sense for targets that run a single
  #       command such as cxx.run(), java.run(), etc.
  additional_args = get_additional_args_for(node_name)

  # Ensure that the output directories exist.
  created_dirs = set()
  for directory in (os.path.dirname(x) for x in node.output_files):
    if directory not in created_dirs:
      os.makedirs(directory, exist_ok=True)
      created_dirs.add(directory)

  # Update the environment and working directory.
  old_env = os.environ.copy()
  os.environ.update(node.environ or {})
  if node.cwd:
    os.chdir(node.cwd)

  # Used to print the command-list on failure.
  def print_command_list(current=-1):
    error('Command list:'.format(node.name))
    for i, cmd in enumerate(node.commands):
      error('>' if current == i else ' ', '$', ' '.join(map(shlex.quote , cmd)))

  # Execute the subcommands/
  for i, cmd in enumerate(node.commands):
    # Add the additional_args to the last command in the chain.
    if i == len(node.commands) - 1:
      cmd = cmd + additional_args
    code = subprocess.call(cmd)
    if code != 0:
      error('\n' + '-'*60)
      error('fatal: "{}" exited with code {}.'.format(node.name, code))
      print_command_list(i)
      error('-'*60 + '\n')
      return code

  # Check if all output files have been produced by the commands.
  missing_files = [x for x in node.output_files if not os.path.exists(x)]
  if missing_files:
    error('\n' + '-'*60)
    error('fatal: "{}" produced only {} of {} listed output files.'.format(node.name,
        len(node.output_files) - len(missing_files), len(node.output_files)))
    error('The missing files are:')
    for x in missing_files:
      print('  -', x)
    print_command_list()
    error('-'*60 + '\n')
    return 1

  return 0


def show_build_node(graph, node_name):
  try:
    node = graph[node_name]
  except KeyError:
    error('fatal: build node "{}" does not exist'.format(node_name))
    return 1
  json.dump(node._asdict(), sys.stdout, indent=2)
  return 0


def list_build_nodes(graph):
  for node in sorted(graph.nodes(), key=lambda x: x.name):
    print(node.name)
  return 0


def prepare_target_list(targets):
  """
  Parses a list of targets specified on the command-line passed to --build
  or --clean, converting them to absolute target names.
  """

  main_build_cell = craftr.cache['main_build_cell']
  result = []
  for target in targets:
    target, sep, args = target.partition('=')
    if target.startswith(':'):
      target = '//' + main_build_cell + target
    result.append((target, args))
  return result


def main(argv=None):
  if argv is None:
    argv = sys.argv[1:]
  if not argv:
    parser.print_usage()
    return 0

  args = parser.parse_args(argv)

  # Handle --quickstart
  if args.quickstart:
    return quickstart(args.quickstart)

  # Handle --list-quickstart
  if args.list_quickstart:
    for directory in module.package.directory.joinpath('examples').iterdir():
      if directory.is_dir():
        print('-', directory.name)
    return 0

  # Handle --list-tools
  if args.list_tools:
    for tool_file in module.directory.joinpath('tools').iterdir():
      print('-', tool_file.with_suffix('').name)
    return 0

  # Handle --cwd
  if args.cwd:
    try:
      os.chdir(args.cwd)
    except OSError as e:
      error('fatal: could not change to directory "{}" ({})'.format(args.cwd, e))
      return 1

  # Handle --tool
  if args.tool is not None:
    if not args.tool:
      error('fatal: --tool requires at least one argument')
      return 1
    try:
      tool_module = require.try_('./tools/' + args.tool[0])
    except require.TryResolveError:
      error('fatal: no such tool:', args.tool[0])
      return 1
    try:
      old_arg0 = sys.argv[0]
      sys.argv[0] += ' --tool {}'.format(args.tool[0])
      return tool_module.main(args.tool[1:])
    finally:
      sys.argv[0] = old_arg0

  # Handle --run-node if a --build-directory is explicitly specified.
  if (args.build is not NotImplemented or args.clean is not NotImplemented
      or args.configure is not NotImplemented or args.flush
      or args.prepare_build) and args.run_node:
    print(args)
    error('fatal: --run-node can not be combined with other build steps.')
    return 1

  craftr.build_directory = args.build_directory
  if args.run_node and args.build_directory:
    build_graph = craftr.BuildGraph().read(os.path.join(args.build_directory, 'craftr_build_graph.json'))
    return run_build_node(build_graph, args.run_node)
  # Handle --show-node if --build-directory was not explicitly specified.
  if args.show_node and args.build_directory:
    build_graph = craftr.BuildGraph().read(os.path.join(args.build_directory, 'craftr_build_graph.json'))
    return show_build_node(build_graph, args.show_node)
  # Handle --list-nodes
  if args.list_nodes and args.build_directory:
    build_graph = craftr.BuildGraph().read(os.path.join(args.build_directory, 'craftr_build_graph.json'))
    return list_build_nodes(build_graph)

  tags = get_platform_tags()
  if not tags and not args.show_config_tags:
    print('note: unexpected platform "{}"'.format(sys.platform))

  craftr.is_configure = True

  # Handle --release
  if args.release:
    craftr.is_release = True
    craftr.options['build.release'] = True
    tags.add('release')
  else:
    craftr.is_release = False
    tags.add('debug')

  # Initialize configuration platform properties.
  [craftr.options.add_cfg_property(x) for x in tags]

  # Handle --show-platform-tags
  if args.show_config_tags:
    print(','.join(sorted(tags)))
    return 0

  # Handle --config
  if not args.config and os.path.isfile('BUILD.cr.toml'):
    craftr.options.read('BUILD.cr.toml')
  elif args.config:
    craftr.options.read(args.config)

  # Handle --options
  set_options(concat(args.options))

  # Determine the build directory.
  if not args.build_directory:
    if not args.build_root:
      args.build_root = craftr.options.get('build.directory', None)
    if not args.build_root:
      args.build_root = find_build_root()
      if args.build_root and args.build_root != 'build':
        print('note: automatically selected build root directory "{}"'.format(
            args.build_root))
    if not args.build_root:
      args.build_root = 'build'
    mark_build_root(args.build_root)
    mode = 'release' if args.release else 'debug'
    args.build_directory = os.path.join(args.build_root, mode)
    craftr.build_directory = args.build_directory

  # Handle --show-build-directory
  if args.show_build_directory:
    print(craftr.build_directory)
    return 0

  # Handle --flush
  if args.flush and os.path.exists(craftr.build_directory):
    msg = 'note: removing build directory "{}" (--flush)'
    print(msg.format(craftr.build_directory))
    shutil.rmtree(craftr.build_directory)

  # Read in the cache from the previous build.
  cache_file = os.path.join(craftr.build_directory, 'craftr_cache.json')
  if os.path.isfile(cache_file):
    with open(cache_file) as fp:
      try:
        craftr.cache = json.load(fp)
      except json.JSONDecodeError as e:
        print('warn: could not load cache from "{}"'.format(cache_file))

  # Combine --options with the cached options, and set them again.
  craftr.cache['options'] = merge_options(craftr.cache.get('options', []), concat(args.options))
  no_such_options, invalid_options = set_options(craftr.cache['options'])
  if no_such_options:
    print('note: these options can not be removed:', no_such_options)
  if invalid_options:
    print('note: these options can not be set:', invalid_options)

  # Handle --show-config
  if args.show_config:
    toml.dump(craftr.options.data(), sys.stdout)
    return 0

  # Handle --backend, load the backend only if we need it, or it makes
  # sense to validate that the backend exists (eg. on --configure).
  if not args.backend:
    args.backend = craftr.options.get('build.backend', 'ninja')
  if args.configure is not NotImplemented or args.prepare_build or \
      args.build is not NotImplemented or args.clean is not NotImplemented:
    try:
      backend = require.context.require.try_('craftr/backends/' + args.backend, args.backend)
    except require.TryResolveError:
      error('fatal: could not load backend "{}"'.format(args.backend))
      return 1
  else:
    backend = None

  build_graph = None
  build_graph_file = os.path.join(craftr.build_directory, 'craftr_build_graph.json')

  # Handle --configure
  if args.configure is not NotImplemented:
    if not args.dry:
      args.save_cache = True
    if not args.configure:
      args.configure = 'BUILD.cr.py'
    if os.path.isdir(args.configure):
      args.configure = posixpath.join(args.configure, 'BUILD.cr.py')
    if not os.path.isabs(args.configure):
      args.configure = './' + args.configure
    build_module = require.new('.').resolve(args.configure)
    with require.context.push_main(build_module):
      require.context.load_module(build_module)
      craftr.cache['main_build_cell'] = craftr.BuildCell(build_module.package).name
    targets = list(concat(x.targets.values() for x in craftr.cells.values()))
    for target in targets:
      target.complete()
    for target in targets:
      target.translate()
    actions = list(concat(x.actions.values() for x in targets))
    print('note: generated', len(actions), plural('action', len(actions)),
          'from', len(targets), plural('target', len(targets)))
    if not args.dry:
      build_graph = craftr.BuildGraph().from_actions(actions)
      print('note: writing "{}"'.format(build_graph_file))
      build_graph.write(build_graph_file)

  # Handle --save-cache
  if args.save_cache:
    print('note: writing "{}"'.format(cache_file))
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, 'w') as fp:
      json.dump(craftr.cache, fp)

  # Load the build graph from file if we need it.
  if not build_graph and (args.prepare_build
      or args.run_node or args.show_node or args.list_nodes
      or args.dotviz is not NotImplemented or args.build is not NotImplemented
      or args.clean is not NotImplemented):
    if args.dotviz is NotImplemented:
      print('note: loading "{}"'.format(build_graph_file))
    build_graph = craftr.BuildGraph().read(build_graph_file)

  # Handle --run-node if --build-directory was not explicitly specified.
  if args.run_node:
    return run_build_node(build_graph, args.run_node)

  # Handle --show-node if --build-directory was not explicitly specified.
  if args.show_node:
    return show_build_node(build_graph, args.show_node)

  # Handle --list-nodes if --build-directory was not explicitly specified.
  if args.list_nodes:
    return list_build_nodes(build_graph)

  # Handle --dotviz
  if args.dotviz is not NotImplemented:
    if args.dotviz is None:
      build_graph.dotviz(sys.stdout)
    else:
      with open(args.dotviz, 'w') as fp:
        build_graph.dotviz(fp)
    return 0

  # Handle --clean
  if args.clean is not NotImplemented:
    build_graph.deselect_all()
    targets, args = zip(*prepare_target_list(args.clean or []))
    if any(args):
      error('fatal: can not pass additional arguments to targets in --clean')
      return 1
    build_graph.select(targets)
    clean_args = list(concat(map(shlex.split, args.clean_args)))
    backend.clean(craftr.build_directory, build_graph, args)

  # Handle --prepare-build
  if args.prepare_build or args.build is not NotImplemented:
    backend.prepare_build(craftr.build_directory, build_graph, args)

  # Handle --build
  if args.build is not NotImplemented:
    build_graph.deselect_all()

    # We write this into another JSON cache to populate additional
    # arguments to already configured tasks.
    additional_args = {}
    for target, target_args in prepare_target_list(args.build):
      if target_args:
        additional_args[target] = target_args
      build_graph.select(target)

    # Write the file, or ensure it does not exist.
    additional_args_file = os.path.join(craftr.build_directory, 'craftr_additional_args.json')
    if additional_args:
      print('note: writing "{}"'.format(additional_args_file))
      with open(additional_args_file, 'w') as fp:
        json.dump(additional_args, fp)
    else:
      with contextlib.suppress(FileNotFoundError):
        os.remove(additional_args_file)

    try:
      build_args = list(concat(map(shlex.split, args.build_args)))
      backend.build(craftr.build_directory, build_graph, args)
    finally:
      with contextlib.suppress(FileNotFoundError):
        os.remove(additional_args_file)


def quickstart(language):
  directory = module.package.directory.joinpath('examples', language)
  if not directory.is_dir():
    error('fatal: quickstart "{}" does not exist'.format(directory))
    return 1

  def copytree(src, dst):
    for item in os.listdir(src):
      s = os.path.join(src, item)
      d = os.path.join(dst, item)
      if os.path.isdir(s):
        os.makedirs(d, exist_ok=True)
        copytree(s, d)
      else:
        if not os.path.isfile(d):
          print('write:', d)
          shutil.copy2(s, d)
        else:
          print('skip:', d, '(file already exists)')

  copytree(str(directory), '.')


if require.main == module:
  sys.exit(main())

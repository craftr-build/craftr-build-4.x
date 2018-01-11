"""
Command-line entry point for the Craftr build system.
"""

import argparse
import collections
import contextlib
import functools
import json
import os
import platform
import posixpath
import re
import shlex
import shutil
import subprocess
import sys
import toml

import craftr from 'craftr'
import utils, {plural, stream.concat as concat, stream.chain as chain} from 'craftr/utils'

error = functools.partial(print, file=sys.stderr)


parser = argparse.ArgumentParser(
  formatter_class=utils.ReindentHelpFormatter,
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
  '--debug',
  action='store_true',
  help='Configure a debug build. Default'
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
  '-rc', '--reconfigure',
  metavar='BUILDSCRIPT',
  nargs='?',
  default=NotImplemented,
  help='Same as --configure, only that previously defined options are '
       'inherited, including the mode (--release or --debug) and the '
       'BUILDSCRIPT if no other explicit value is specified. If there was '
       'no previous configuration, acts like --configure.'
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
  '--run-action',
  metavar='NAME[^HASH]',
  help='Execute the command for the specified build-action. Build action names '
       'are formatted as `//<cell>:<target>#<action>`. This can be used '
       'internally by build backends to implement deduplication. This option '
       'requires the --build-directory to be set.'
)

parser.add_argument(
  '--run-action-index',
  metavar='INDEX',
  type=int,
  help='Use this option for actions that are executed for each input/output '
       'pair to specify the pair index. If a action is marked as "foreach" and '
       'this argument is not present, an error will be presented.'
)

parser.add_argument(
  '--show-action',
  metavar='NAME',
  help='Show the information for the specified build action.'
)

parser.add_argument(
  '--list-actions',
  action='store_true',
  help='List all build actions and exit.'
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
  '--dotviz-targets',
  metavar='FILE',
  nargs='?',
  default=NotImplemented,
  help='Render a .dot graph file to the specified FILE or stdout and exit. '
       'This option requires --configure as otherwise the target graph '
       'is not available.'
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


def find_build_root():
  results = []
  for name in os.listdir('.'):
    if os.path.isfile(os.path.join(name, 'craftr_build_root.json')):
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
  result = collections.OrderedDict()
  for option in concat(opts):
    key, sep, value = option.partition('=')
    if not sep:
      result.pop(key, None)
    else:
      result[key] = value
  return [k + '=' + v for k, v in result.items()]


def get_additional_args_for(action_name):
  """
  In the --build step, a `craftr_additional_args.json` file may be present
  which specifies additional arguments passed to a target via the command-line.
  This extracts the additional arguments for the specified *action_name*, falling
  back to the action's target if such an entry exists.
  """

  additional_args_file = os.path.join(craftr.build_directory, 'craftr_additional_args.json')
  if not os.path.isfile(additional_args_file):
    return []
  with open(additional_args_file, 'r') as fp:
    additional_args = json.load(fp)
  try:
    return shlex.split(additional_args[action_name])
  except KeyError:
    pass
  target_name = action_name.partition('#')[0]
  try:
    return shlex.split(additional_args[target_name])
  except KeyError:
    pass
  return []


def substitute_inputs_outputs(command, iofiles):
  """
  Substitutes the $in and $out references in *command* for the *inputs*
  and *outputs*.
  """

  def expand(commands, var, files):
    regexp = re.compile('(\\${}\\b)(\[\d+\])?(\.[\w\d]+\\b)?'.format(re.escape(var)))
    offset = 0
    for i in range(len(commands)):
      i += offset
      match = regexp.search(commands[i])
      if not match: continue
      prefix, suffix = commands[i][:match.start()], commands[i][match.end():]
      subst = [prefix + x + suffix for x in files]
      index = match.group(2)
      suffix = match.group(3)
      if index:
        subst = [subst[int(index[1:-1])]]
      if suffix:
        subst = [craftr.path.setsuffix(x, suffix) for x in subst]
      commands[i:i+1] = subst
      offset += len(subst) - 1

  expand(command, 'in', iofiles.inputs)
  expand(command, 'out', iofiles.outputs)
  expand(command, 'optionalout', iofiles.optional_outputs)
  return command


def run_build_action(graph, node_name, index):
  if '^' in node_name:
    node_name, node_hash = node_name.split('^', 1)
  else:
    node_hash = None
  if node_name.startswith(':'):
    node_name = '//' + craftr.cache['main_build_cell'] + node_name

  try:
    node = graph[node_name]
  except KeyError:
    error('fatal: build node "{}" does not exist'.format(node_name))
    return 1

  if node.foreach and index is None:
    error('fatal: --run-action-index is required for foreach action')
    return 1
  if not node.foreach and index is not None:
    error('fatal: --run-action-index is incompatible with non-foreach action')
    return 1
  if not node.foreach:
    index = 0

  if node_hash is not None and node_hash != graph.hash(node):
    error('fatal: build node hash inconsistency, maybe try --prepare-build')
    return 1

  files = node.files[index]

  # TODO: The additional args feature should be explicitly supported by the
  #       build node, allowing it to specify a position where the additional
  #       args will be rendered.
  #       Usually, the option only makes sense for targets that run a single
  #       command such as cxx.run(), java.run(), etc.
  additional_args = get_additional_args_for(node_name)

  # Ensure that the output directories exist.
  created_dirs = set()
  for directory in (os.path.dirname(x) for x in chain(files.outputs, files.optional_outputs)):
    if directory not in created_dirs and directory:
      os.makedirs(directory, exist_ok=True)
      created_dirs.add(directory)

  # Update the environment and working directory.
  old_env = os.environ.copy()
  os.environ.update(node.environ or {})
  if node.cwd:
    os.chdir(node.cwd)

  # Used to print the command-list on failure.
  def print_command_list(current=-1):
    error('Command list:'.format(node.identifier()))
    for i, cmd in enumerate(node.commands):
      error('>' if current == i else ' ', '$', ' '.join(map(shlex.quote , cmd)))

  # Execute the subcommands.
  for i, cmd in enumerate(node.commands):
    cmd = substitute_inputs_outputs(cmd, files)
    # Add the additional_args to the last command in the chain.
    if i == len(node.commands) - 1:
      cmd = cmd + additional_args
    try:
      code = subprocess.call(cmd)
    except OSError as e:
      error(e)
      code = 127
    if code != 0:
      error('\n' + '-'*60)
      error('fatal: "{}" exited with code {}.'.format(node.identifier(), code))
      print_command_list(i)
      error('-'*60 + '\n')
      return code

  # Check if all output files have been produced by the commands.
  missing_files = [x for x in files.outputs if not os.path.exists(x)]
  if missing_files:
    error('\n' + '-'*60)
    error('fatal: "{}" produced only {} of {} listed output files.'.format(node.identifier(),
        len(files.outputs) - len(missing_files), len(files.outputs)))
    error('The missing files are:')
    for x in missing_files:
      error('  -', x)
    print_command_list()
    error('-'*60 + '\n')
    return 1

  return 0


def show_build_action(graph, action_name):
  if action_name.startswith(':'):
    action_name = '//' + craftr.cache['main_build_cell'] + action_name
  try:
    action = graph[action_name]
  except KeyError:
    error('fatal: build action "{}" does not exist'.format(action_name))
    return 1
  data = action.as_json()
  data['hash'] = graph.hash(action)
  json.dump(data, sys.stdout, sort_keys=True, indent=2)
  print()
  return 0


def list_build_actions(graph):
  for action in sorted(graph.actions(), key=lambda x: x.identifier()):
    print(action.identifier())
  return 0


def dotviz_targets(targets, fp):
  if fp is None:
    fp = sys.stdout
  elif isinstance(fp, str):
    with open(fp, 'w') as fp:
      return dotviz_targets(targets, fp)
  fp.write('digraph "craftr-targets" {\n')
  for target in sorted(targets, key=lambda x: x.identifier()):
    fp.write('\t{} [label="{}" style="rounded" shape="box"];\n'.format(id(target), target.identifier()))
    for dep in target.deps(transitive=False, children=False, parent=False):
      fp.write('\t\t{} -> {};\n'.format(id(dep), id(target)))
    for child in target.children:
      fp.write('\t\t{} -> {} [style="dashed" arrowhead="odiamond"];\n'.format(id(child), id(target)))
  fp.write('}\n')


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

  # Validate some parameter combinations.
  if (args.reconfigure is not NotImplemented and
      args.configure is not NotImplemented):
    error('fatal: --reconfigure and --configure are incompatible')
    return 1
  if args.release and args.debug:
    error('fatal: --release and --debug are incompatible')
    return 1

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

  # Handle --run-action if a --build-directory is explicitly specified.
  if (args.build is not NotImplemented or args.clean is not NotImplemented
      or args.configure is not NotImplemented or args.flush
      or args.prepare_build) and args.run_action:
    print(args)
    error('fatal: --run-action can not be combined with other build steps.')
    return 1

  craftr.build_directory = args.build_directory
  if args.run_action and args.build_directory:
    build_graph = craftr.BuildGraph().read(os.path.join(args.build_directory, 'craftr_build_graph.json'))
    return run_build_action(build_graph, args.run_action, args.run_action_index)
  # Handle --show-action if --build-directory was not explicitly specified.
  if args.show_action and args.build_directory:
    build_graph = craftr.BuildGraph().read(os.path.join(args.build_directory, 'craftr_build_graph.json'))
    return show_build_action(build_graph, args.show_action)
  # Handle --list-actions
  if args.list_actions and args.build_directory:
    build_graph = craftr.BuildGraph().read(os.path.join(args.build_directory, 'craftr_build_graph.json'))
    return list_build_actions(build_graph)

  tags = get_platform_tags()
  if not tags and not args.show_config_tags:
    print('note: unexpected platform "{}"'.format(sys.platform))

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

  # Determine the build root directory.
  if not args.build_root:
    if args.build_directory:
      args.build_root = args.build_directory
    else:
      args.build_root = craftr.options.get('build.directory', None)
  if not args.build_root:
    args.build_root = find_build_root()
    if args.build_root and args.build_root != 'build':
      print('note: automatically selected build root directory "{}"'.format(
          args.build_root))
  if not args.build_root:
    args.build_root = 'build'

  # Read the build root cache.
  build_root_file = os.path.join(args.build_root, 'craftr_build_root.json')
  build_root_cache = {}
  if os.path.isfile(build_root_file):
    with open(build_root_file, 'r') as fp:
      try:
        build_root_cache = json.load(fp)
      except json.JSONDecodeError as e:
        print('warn: could not load {!r}: {}'.format(build_root_file, e))

  # Handle --reconfigure
  if args.reconfigure is not NotImplemented:
    if args.reconfigure is None:
      args.reconfigure = build_root_cache.get('build_script', None)
      if args.reconfigure:
        print('note: inheriting build script:', args.reconfigure)
    args.configure = args.reconfigure

  craftr.is_configure = True

  # Fall back to --release or --debug from the build root cache.
  if not args.release and not args.debug:
    if build_root_cache.get('build_mode', 'debug') == 'release':
      args.release = True
    print('note: inheriting build mode:', 'release' if args.release else 'debug')

  # Handle --release
  if args.release:
    craftr.is_release = True
    craftr.options['build.release'] = True
    tags.add('release')
  else:
    args.debug = True
    craftr.is_release = False
    tags.add('debug')

  # Determine the build directory.
  if not args.build_directory:
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

  # Handle --options (eventually combined with cached options).
  if args.reconfigure is not NotImplemented:
    # Combine --options with the cached options.
    prev_options = craftr.cache.get('options', [])
    if prev_options:
      print('note: inheriting previous build options:', ' '.join(map(shlex.quote, prev_options)))
    craftr.cache['options'] = merge_options(prev_options, concat(args.options))
  else:
    # Only use the new options.
    craftr.cache['options'] = list(concat(args.options))
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

  # Validate --dotviz-targets
  if args.dotviz_targets is not NotImplemented:
    if args.configure is NotImplemented:
      error('fatal: --dotviz-targets requires --configure')
      return 1

  # Handle --configure
  if args.configure is not NotImplemented:
    if not args.dry:
      args.save_cache = True
    if not args.configure:
      args.configure = 'BUILD.cr.py'
    if os.path.isdir(args.configure):
      args.configure = posixpath.join(args.configure, 'BUILD.cr.py')
    if not os.path.isabs(args.configure):
      args.configure = './' + os.path.normpath(args.configure)
    build_module = require.new('.').resolve(args.configure)
    with require.context.push_main(build_module):
      require.context.load_module(build_module)
      craftr.cache['main_build_cell'] = craftr.Namespace.from_module(build_module).name
    targets = list(concat(x.targets.values() for x in craftr.Namespace.all()))

    # Handle --dotviz-targets
    if args.dotviz_targets is not NotImplemented:
      dotviz_targets(targets, args.dotviz_targets)
      return 0

    for target in targets:
      target.translate()
    actions = list(concat(x.actions() for x in targets))
    print('note: generated', len(actions), plural('action', len(actions)),
          'from', len(targets), plural('target', len(targets)))
    if not args.dry:
      build_graph = craftr.BuildGraph().from_actions(actions)
      print('note: writing "{}"'.format(build_graph_file))
      build_graph.write(build_graph_file)

    build_root_cache['build_mode'] = 'release' if craftr.is_release else 'debug'
    build_root_cache['build_script'] = args.configure
    with open(build_root_file, 'w') as fp:
      json.dump(build_root_cache, fp, indent=2, sort_keys=True)

  # Handle --save-cache
  if args.save_cache:
    print('note: writing "{}"'.format(cache_file))
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, 'w') as fp:
      json.dump(craftr.cache, fp, sort_keys=True, indent=2)

  # Load the build graph from file if we need it.
  if not build_graph and (args.prepare_build
      or args.run_action or args.show_action or args.list_actions
      or args.dotviz is not NotImplemented or args.build is not NotImplemented
      or args.clean is not NotImplemented):
    if args.dotviz is NotImplemented:
      print('note: loading "{}"'.format(build_graph_file))
    build_graph = craftr.BuildGraph().read(build_graph_file)

  # Handle --run-action if --build-directory was not explicitly specified.
  if args.run_action:
    return run_build_action(build_graph, args.run_action, args.run_action_index)

  # Handle --show-action if --build-directory was not explicitly specified.
  if args.show_action:
    return show_build_action(build_graph, args.show_action)

  # Handle --list-actions if --build-directory was not explicitly specified.
  if args.list_actions:
    return list_build_actions(build_graph)

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
    if args.clean:
      targets, args = zip(*prepare_target_list(args.clean))
      if any(args):
        error('fatal: can not pass additional arguments to targets in --clean')
        return 1
      build_graph.select(targets)
    args.clean_args = list(concat(map(shlex.split, args.clean_args)))
    res = backend.clean(craftr.build_directory, build_graph, args)
    if res not in (0, None):
      return res

  # Handle --prepare-build
  if args.prepare_build or args.build is not NotImplemented:
    res = backend.prepare_build(craftr.build_directory, build_graph, args)
    if res not in (0, None):
      return res

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
      args.build_args = list(concat(map(shlex.split, args.build_args)))
      res = backend.build(craftr.build_directory, build_graph, args)
    finally:
      with contextlib.suppress(FileNotFoundError):
        os.remove(additional_args_file)
    if res not in (0, None):
      return res

  return 0


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

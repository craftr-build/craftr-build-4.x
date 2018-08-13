
import argparse
import contextlib
import io
import os
import nr.fs
import subprocess
import sys

from craftr import api
from craftr.core.build import to_graph


@contextlib.contextmanager
def open_cli_file(filename, mode):
  if not filename:
    # TODO: Handle r/rb/w/w/b
    yield sys.stdout
  else:
    with open(filename, mode) as fp:
      yield fp


def get_argument_parser(prog=None):
  parser = argparse.ArgumentParser(
    prog=prog,
    formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=70, width=100))

  group = parser.add_argument_group('Configuration')

  group.add_argument(
    '--variant',
    metavar='[=debug]',
    choices=('debug', 'release'),
    default='debug',
    help='Choose the build variant (debug|release).')

  group.add_argument(
    '--project',
    default='build.craftr',
    metavar='PATH',
    help='The Craftr project file or directory to load.')

  group.add_argument(
    '--module-path',
    action='append',
    default=[],
    metavar='PATH',
    help='Additional module search paths.')

  group.add_argument(
    '--config-file',
    default=None,
    metavar='PATH',
    help='Load the specified configuration file. Defaults to '
         '"build.craftr.toml" or "build.craftr.json" in the project '
         'directory if the file exists.')

  group.add_argument(
    '-O', '--option',
    dest='options',
    action='append',
    default=[],
    metavar='K=V',
    help='Override an option value.')

  group.add_argument(
    '--build-root',
    default='build',
    metavar='PATH=[build]',
    help='The build root directory. When used, this option must be specified '
         'with every invokation of Craftr, even after the config step.')

  group.add_argument(
    '--backend',
    default=None,
    metavar='MODULE',
    help='Override the build backend. Can also be specified with the '
         'build:backend option. Defaults to "net.craftr.backend.ninja".')

  group = parser.add_argument_group('Configure, build and clean')

  group.add_argument(
    'targets',
    nargs='*',
    metavar='[TARGET [...]]',
    help='Allows you to explicitly specify the targets that should be built '
         'and/or cleaned with the --build and --clean steps. A target '
         'specifier is of the form "[scope@]target[:operator]. If the scope '
         'is omitted, it falls back to the project\'s scope. If the operator '
         'is not specified, all non-explicit operators of the target are used. '
         'Logical children of one target are automatically included when their '
         'parent target is matched.')

  group.add_argument(
    '-c', '--config',
    action='store_true',
    help='Configure step. Run the project build script and serialize the '
         'build information. This needs to be re-run when the build backend '
         'is changed.')

  group.add_argument(
    '-b', '--build',
    action='store_true',
    help='Build step. This must be used after or together with --config.')

  group.add_argument(
    '--clean',
    action='store_true',
    help='Clean step.')

  group.add_argument(
    '-v', '--verbose',
    action='store_true',
    help='Enable verbose output in the --build and/or --clean steps.')

  group.add_argument(
    '-r', '--recursive',
    action='store_true',
    help='Clean build sets recursively.')

  group = parser.add_argument_group('Tools and debugging')

  group.add_argument(
    '--tool',
    nargs='...',
    metavar='TOOLNAME [ARG [...]]',
    help='Invoke a Craftr tool.')

  group.add_argument(
    '--dump-graphviz',
    nargs='?',
    default=NotImplemented,
    metavar='FILE',
    help='Dump a GraphViz representation of the build graph to stdout or '
         'the specified FILE.')

  group.add_argument(
    '--dump-svg',
    nargs='?',
    default=NotImplemented,
    metavar='FILE',
    help='Render an SVG file of the build graph\'s GraphViz representation '
         'to stdout or the specified FILE. Override the layout engine with '
         'the DOTENGINE environment variable (defaults to "dot").')

  group.add_argument(
    '--notify',
    action='store_true',
    help='Send a notification when the build completed. Requires the ntfy '
         'module to be installed.'
  )

  return parser


def main(argv=None, prog=None):
  if argv is None:
    argv = sys.argv[1:]

  # Workaround for the argparse.REMAINDER mode to ensure that ALL arguments
  # after this flag are consumed and not just some that look like they could
  # not belong to other arguments...
  try:
    tool_index = argv.index('--tool')
  except ValueError:
    tool_argv = None
  else:
    argv, tool_argv = argv[:tool_index+1], argv[tool_index+1:]

  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)

  if args.notify:
    try:
      import ntfy
    except ImportError:
      print('warning: ntfy module is not available, --notify is ignored.')
      ntfy = None

  if nr.fs.isdir(args.project):
    args.project = nr.fs.join(args.project, 'build.craftr')
  if not args.config_file:
    args.config_file = nr.fs.join(nr.fs.dir(args.project), 'build.craftr.toml')
    if not nr.fs.isfile(args.config_file):
      args.config_file = nr.fs.join(nr.fs.dir(args.project), 'build.craftr.json')
      if not nr.fs.isfile(args.config_file):
        args.config_file = None

  for x in args.targets[:]:
    if '=' in x:
      args.options.append(x)
      args.targets.remove(x)

  # Create a new session.
  build_directory = nr.fs.join(args.build_root, args.variant)
  session = api.session = api.Session(args.build_root, build_directory, args.variant)
  session.add_module_search_path(args.module_path)
  if args.config_file:
    session.load_config(args.config_file)
  for opt in args.options or ():
    key, value = opt.partition('=')[::2]
    session.options[key] = value

  if args.tool is not None:
    tool_name, argv = tool_argv[0], tool_argv[1:]
    module = session.load_module('net.craftr.tool.' + tool_name).namespace
    return module.main(argv, 'craftr --tool {}'.format(tool_name))

  graph_file = nr.fs.join(session.build_root, 'craftr_graph.{}.json'.format(session.build_variant))
  if args.config:
    session.load_module_from_file(args.project, is_main=True)
    nr.fs.makedirs(nr.fs.dir(graph_file))
    session.save(graph_file)
  else:
    session.load(graph_file)

  # Determine the build sets that are supposed to be built.
  if args.targets:
    build_sets = []
    for name in args.targets:
      if '@' in name:
        scope, name = name.partition('@')[::2]
      else:
        scope = session.main_module
      if ':' in name:
        target_name, op_name = name.partition(':')[::2]
      else:
        target_name, op_name = name, None

      # Find the target with the exact name and subtargets.
      full_name = scope + '@' + target_name
      prefix = full_name + '/'
      targets = []
      for target in session.targets:
        if target.id == full_name or target.id.startswith(prefix):
          targets.append(target)

      if not targets:
        print('error: no targets matched {!r}'.format(full_name))
        return 1

      # Find all matching operators and add their build sets.
      found_sets = False
      for target in targets:
        for op in target.operators:
          if (not op_name and not op.explicit) or op.name.partition('#')[0] == op_name:
            found_sets = True
            build_sets += op.build_sets

      if not found_sets:
        print('error: no operators matched {!r}'.format(op_name))
        return 1

  else:
    build_sets = [x for x in session.all_build_sets() if not x.operator.explicit]

  if args.dump_graphviz is not NotImplemented:
    with open_cli_file(args.dump_graphviz, 'w') as fp:
      to_graph(session).render(fp)
    return 0

  if args.dump_svg is not NotImplemented:
    dotstr = to_graph(session).render().encode('utf8')
    with open_cli_file(args.dump_svg, 'w') as fp:
      command = [os.environ.get('DOTENGINE', 'dot'), '-T', 'svg']
      p = subprocess.Popen(command, stdout=fp, stdin=subprocess.PIPE)
      p.communicate(dotstr)
    return 0

  if not args.backend:
    args.backend = session.options.get('build:backend', 'net.craftr.backend.ninja')
  backend = session.load_module(args.backend).namespace
  if args.config:
    backend.export()
  if args.clean:
    backend.clean(build_sets, recursive=args.recursive, verbose=args.verbose)
  if args.build:
    res = backend.build(build_sets, verbose=args.verbose)
    if args.notify and ntfy:
      ntfy.notify('Build completed.' if res == 0 else 'Build errored.', 'Craftr')


if __name__ == '__main__':
  sys.exit(main())

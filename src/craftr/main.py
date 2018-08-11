
import argparse
import contextlib
import io
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
  parser = argparse.ArgumentParser(prog=prog)

  # Configuration options

  parser.add_argument('--project', default='build.craftr',
    help='The Craftr project file or directory to load.')
  parser.add_argument('--variant',
    choices=('debug', 'release'), default='debug',
    help='The build variant. Defaults to debug.')
  parser.add_argument('--build-root', default='build',
    help='The build root directory. Defaults to build.')
  parser.add_argument('--build-directory',
    help='The build output directory. Defaults to {build_root}/{variant}.')
  parser.add_argument('--backend', default='craftr/backends/python',
    help='The build backend to use.')
  parser.add_argument('--verbose', action='store_true')
  parser.add_argument('--recursive', action='store_true')

  # Invokation options

  parser.add_argument('-c', '--config', action='store_true',
    help='Configure the build. This will execute the build script and '
         'export the build graph to the build directory (depending on '
         'the backend).')
  parser.add_argument('-b', '--build', action='store_true',
    help='Execute the build. Additional arguments are treated as '
         'the targets that are to be built.')
  parser.add_argument('--clean', action='store_true',
    help='Clean the build output files. Additional arguments are '
         'treated as the targets that are to be cleaned.')

  # Meta options

  parser.add_argument('--tool', nargs='...', help='Invoke a tool')
  parser.add_argument('--dump-graphviz', nargs='?', default=NotImplemented,
    help='Dump a GraphViz representation of the build graph to stdout.')
  parser.add_argument('--dump-svg', nargs='?', default=NotImplemented,
    help='Render an SVG file of the build graph\'s GraphViz representation. '
         'Requires the `dot` command to be available.')

  return parser


def main(argv=None, prog=None):
  parser = get_argument_parser(prog)
  args, selection = parser.parse_known_args(argv)

  for x in selection:
    if x.startswith('-'):
      parser.error('unknown option: {}'.format(x))

  if not args.build_directory:
    args.build_directory = nr.fs.join(args.build_root, args.variant)

  if nr.fs.isdir(args.project):
    args.project = nr.fs.join(args.project, 'build.craftr')

  # Create a new session.
  session = api.session = api.Session(args.build_root, args.build_directory, args.variant)

  if args.tool is not None:
    if not args.tool:
      parser.error('missing arguments for --tool')
    tool_name, argv = args.tool[0], args.tool[1:]
    module = session.load_module('craftr/tools/' + tool_name).namespace
    return module.main(argv, 'craftr --tool {}'.format(tool_name))

  backend = session.load_module(args.backend).namespace

  if args.config:  # TODO: or no serialized version of the build graph available
    module = session.load_module_from_file(args.project, is_main=True)
  else:
    raise NotImplementedError('build graph deserialization not implemented')

  # Determine the build sets that are supposed to be built.
  if selection:
    build_sets = []
    for name in selection:
      if '@' in name:
        scope, name = name.partition('@')[::2]
      else:
        scope = module.scope.name
      if ':' in name:
        target_name, op_name = name.partition(':')[::2]
      else:
        target_name, op_name = name, None
      target = session.targets[scope + '@' + target_name]
      for op in target.operators:
        if (not op_name and not op.explicit) or op.id.partition('#')[0] == op_name:
          build_sets += op.build_sets
  else:
    build_sets = [x for x in session.all_build_sets() if not x.operator.explicit]

  if args.dump_graphviz is not NotImplemented:
    with open_cli_file(args.dump_graphviz, 'w') as fp:
      to_graph(session).render(fp)
    return 0

  if args.dump_svg is not NotImplemented:
    dotstr = to_graph(session).render().encode('utf8')
    with open_cli_file(args.dump_svg, 'w') as fp:
      command = ['dot', '-T', 'svg']
      p = subprocess.Popen(command, stdout=fp, stdin=subprocess.PIPE)
      p.communicate(dotstr)
    return 0

  if args.config:
    backend.export()
  if args.clean:
    backend.clean(build_sets, args.recursive, args.verbose)
  if args.build:
    backend.build(build_sets, args.verbose)


if __name__ == '__main__':
  sys.exit(main())

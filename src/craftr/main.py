
import argparse
import contextlib
import io
import nr.fs
import subprocess
import sys

from craftr import api
from craftr.core.build import to_graph, execute


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

  # Build options

  parser.add_argument('--variant',
    choices=('debug', 'release'), default='debug',
    help='The build variant. Defaults to debug.')
  parser.add_argument('--build-directory',
    help='The build output directory. Defaults to build/{variant}.')

  # Meta options

  parser.add_argument('--dump-graphviz', nargs='?', default=NotImplemented,
    help='Dump a GraphViz representation of the build graph to stdout.')
  parser.add_argument('--dump-svg', nargs='?', default=NotImplemented,
    help='Render an SVG file of the build graph\'s GraphViz representation. '
         'Requires the `dot` command to be available.')

  return parser


def main(argv=None, prog=None):
  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)

  if not args.build_directory:
    args.build_directory = nr.fs.join('build', args.variant)

  # Create a new session.
  session = api.session = api.Session(args.build_directory)

  module = session.load_module_from_file('build.craftr', is_main=True)

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

  execute(session)


if __name__ == '__main__':
  sys.exit(main())

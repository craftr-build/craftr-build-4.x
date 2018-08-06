
import argparse
import sys

from craftr.api import globals as _globals
from craftr.core.build import dump_graphviz


def get_argument_parser(prog=None):
  parser = argparse.ArgumentParser(prog=prog)
  parser.add_argument('--dump-graphviz', action='store_true',
    help='Dump a GraphViz representation of the build graph to stdout.')
  parser.add_argument('--dump-svg', action='store_true',
    help='Render an SVG file of the build graph\'s GraphViz representation. '
         'Requires the `dot` command to be available.')
  return parser


def main(argv=None, prog=None):
  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)

  # Create a new session.
  session = _globals._session = _globals.Session()

  # TODO: Determine scope name and version.
  with session.enter_scope('main'):
    with open('build.craftr') as fp:
      import types
      m = types.ModuleType('build')
      exec(compile(fp.read(), 'build.craftr', 'exec'), vars(m))

  if args.dump_graphviz:
    dump_graphviz(session)
    return 0

  if args.dump_svg:
    import io, subprocess
    fp = io.StringIO()
    dump_graphviz(session, fp=fp)
    p = subprocess.Popen(['dot', '-T', 'svg'], stdin=subprocess.PIPE)
    p.communicate(fp.getvalue().encode('utf8'))
    return 0


if __name__ == '__main__':
  sys.exit(main())

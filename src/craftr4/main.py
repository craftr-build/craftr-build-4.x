
import argparse
import sys

from craftr4.api.globals import _session_stack, session
from craftr4.api.session import Session
from craftr4.core.build import dump_graphviz


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
  _session_stack.push(Session())

  # TODO: Determine scope name and version.
  with session.enter_scope('main', '1.0-0'):
    with open('build.craftr') as fp:
      import types
      m = types.ModuleType('build')
      exec(compile(fp.read(), 'build.craftr', 'exec'), vars(m))

  if args.dump_graphviz:
    dump_graphviz(session.build_master)
    return 0

  if args.dump_svg:
    import io, subprocess
    fp = io.StringIO()
    dump_graphviz(session.build_master, fp=fp)
    p = subprocess.Popen(['dot', '-T', 'svg'], stdin=subprocess.PIPE)
    p.communicate(fp.getvalue().encode('utf8'))
    return 0


if __name__ == '__main__':
  sys.exit(main())

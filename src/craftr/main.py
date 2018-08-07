
import argparse
import nr.fs
import sys

from craftr import api
from craftr.core.build import dump_graphviz

def get_argument_parser(prog=None):
  parser = argparse.ArgumentParser(prog=prog)

  # Build options

  parser.add_argument('--variant',
    choices=('debug', 'release'), default='debug',
    help='The build variant. Defaults to debug.')
  parser.add_argument('--build-directory',
    help='The build output directory. Defaults to build/{variant}.')

  # Meta options

  parser.add_argument('--dump-graphviz', action='store_true',
    help='Dump a GraphViz representation of the build graph to stdout.')
  parser.add_argument('--dump-svg', action='store_true',
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

  # TODO: Determine scope name and version.
  with session.enter_scope('main', '1.0-0', '.'):
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

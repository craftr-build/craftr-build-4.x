
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
  parser = argparse.ArgumentParser(prog=prog)

  parser.add_argument('targets', nargs='*',
    help='The targets to build or clean.')

  # Configuration options

  parser.add_argument('--project', default='build.craftr',
    help='The Craftr project file or directory to load.')
  parser.add_argument('--config-file', default=None,
    help='Load the specified configuration file. Defaults to '
         '"build.craftr.toml" or "build.craftr.json" in the project '
         'directory if the file exists.')
  parser.add_argument('--variant',
    choices=('debug', 'release'), default='debug',
    help='The build variant. Defaults to debug.')
  parser.add_argument('--build-root', default='build',
    help='The build root directory. Defaults to build.')
  parser.add_argument('--build-directory',
    help='The build output directory. Defaults to {build_root}/{variant}.')
  parser.add_argument('--backend', default='craftr/backends/python',
    help='The build backend to use.')
  parser.add_argument('--options', nargs='+',
    help='Specify one or more options.')
  parser.add_argument('--verbose', action='store_true')
  parser.add_argument('--recursive', action='store_true')
  parser.add_argument('--module-path', action='append', default=[],
    help='Additional module search paths.')

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
  args = parser.parse_args(argv)

  if not args.build_directory:
    args.build_directory = nr.fs.join(args.build_root, args.variant)
  if nr.fs.isdir(args.project):
    args.project = nr.fs.join(args.project, 'build.craftr')
  if not args.config_file:
    args.config_file = nr.fs.join(nr.fs.dir(args.project), 'build.craftr.toml')
    if not nr.fs.isfile(args.config_file):
      args.config_file = nr.fs.join(nr.fs.dir(args.project), 'build.craftr.json')
      if not nr.fs.isfile(args.config_file):
        args.config_file = None

  # Create a new session.
  session = api.session = api.Session(args.build_root, args.build_directory, args.variant)
  session.add_module_search_path(args.module_path)
  if args.config_file:
    session.load_config(args.config_file)
  for opt in args.options or ():
    key, value = opt.partition('=')[::2]
    session.options[key] = value

  if args.tool is not None:
    if not args.tool:
      parser.error('missing arguments for --tool')
    tool_name, argv = args.tool[0], args.tool[1:]
    module = session.load_module('craftr/tools/' + tool_name).namespace
    return module.main(argv, 'craftr --tool {}'.format(tool_name))

  graph_file = nr.fs.join(session.build_root, 'craftr_graph.{}.json'.format(session.build_variant))
  if args.config:
    session.load_module_from_file(args.project, is_main=True)
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
          if (not op_name and not op.explicit) or op.id.partition('#')[0] == op_name:
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

  backend = session.load_module(args.backend).namespace
  if args.config:
    backend.export()
  if args.clean:
    backend.clean(build_sets, args.recursive, args.verbose)
  if args.build:
    backend.build(build_sets, args.verbose)


if __name__ == '__main__':
  sys.exit(main())

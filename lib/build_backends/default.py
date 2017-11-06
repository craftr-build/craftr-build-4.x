"""
The default, Python-based build backend.
"""

import {ActionProgress} from '../core/actions'


def build_argparser(parser):
  parser.add_argument('targets', nargs='*', metavar='TARGET')


def build_main(args, session, module):
  # Execute the module.
  require.context.load_module(module)

  # Generate the action graph.
  targets = session.resolve_targets(args.targets) if args.targets else None
  graph = session.build_target_graph().translate(targets)

  # Execute the actions.
  code = 0
  for action in graph.topo_sort():
    if action.check_skip(): continue
    print('[{}]: {}'.format(action.long_name, action.data.get_display(action)))
    progress = ActionProgress(do_buffering=False)
    code = action.execute_with(progress)
    if code != 0:
      print('fatal: action {!r} exited with {}'.format(action.long_name, code))
      return code

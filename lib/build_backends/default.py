"""
The default, Python-based build backend.
"""

import concurrent.futures
import threading
import {ActionProgress} from '../core/actions'
import tty from '../utils/tty'

try: from multiprocessing import cpu_count
except ImportError: cpu_count = lambda: 1


def ellipsize_text(text, w):
  if len(text) > w:
    text = text[:w//2-2] + '...' + text[-w//2+1:]
  return text


class ParallelExecutor:

  def __init__(self, max_workers, num_actions):
    self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    self.num_actions = num_actions
    self.num_actions_processed = 0
    self.iolock = threading.RLock()
    self.datalock = threading.RLock()
    self.futures = []

  def __enter__(self):
    self.pool.__enter__()
    return self

  def __exit__(self, *args):
    print()
    return self.pool.__exit__(*args)

  def put(self, action):
    with self.datalock:
      self.futures.append(self.pool.submit(self._worker, action))

  def pop_done(self):
    with self.datalock:
      completed, running = [], []
      for future in self.futures:
        if future.done():
          completed.append(future)
        else:
          running.append(future)
      self.futures = running
      return completed

  def before_execute(self, action):
    with self.iolock:
      width = tty.terminal_size()[0]
      line = tty.colored(
        '[{}/{} -- {}]:'.format(self.num_actions_processed,
          self.num_actions, action.long_name),
        'cyan'
      ) + ' '
      line += tty.colored(ellipsize_text(action.get_display(), width-len(line)), 'yellow')
      tty.clear_line()
      print('\r', line, sep='', end='')

  def _worker(self, action):
    console = not action.target.console
    progress = ActionProgress(do_buffering=console)
    if console:
      with self.iolock:
        self.before_execute(action)
        action.execute_with(progress)
    else:
      self.before_execute(action)
      action.execute_with(progress)
    with self.iolock:
      self.num_actions_processed += 1
    return action

  def wait(self):
    self.pool.shutdown(wait=True)


def _execute_action(action):
  progress = ActionProgress(do_buffering=action.console)


def build_argparser(parser):
  parser.add_argument('targets', nargs='*', metavar='TARGET')
  parser.add_argument('-j', '--jobs', nargs='+', type=int, default=cpu_count() * 2)


def build_main(args, session, module):
  # Execute the module.
  require.context.load_module(module)

  # Generate the action graph.
  targets = session.resolve_targets(args.targets) if args.targets else None
  graph = session.build_target_graph().translate(targets)
  actions = iter(graph.topo_sort())

  with ParallelExecutor(max_workers=args.jobs, num_actions=len(graph)) as executor:
    done = False
    while not done:
      with executor.iolock:
        for action in (f.result() for f in executor.pop_done()):
          if action.progress.code != 0:
            print('\n[FAIL {}]: {}'.format(action.long_name, action.get_display()))
            action.progress.print_buffer()
            print('craftr: "{}" exited with code {}'.format(
              action.long_name, action.progress.code))
            return action.progress.code
          elif action.progress.buffer_has_content():
            print('\n[{}]: {}'.format(action.long_name, action.get_display()))
            action.progress.print_buffer()
      action = next(actions, None)
      if action is None:
        executor.wait()
        done = True
        continue
      if not action.check_skip():
        executor.put(action)

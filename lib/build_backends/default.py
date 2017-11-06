"""
The default, Python-based build backend.
"""

import concurrent.futures
import threading
import traceback
import {ActionProgress} from '../core/actions'
import tty from '../utils/tty'

try: from multiprocessing import cpu_count
except ImportError: cpu_count = lambda: 1


def ellipsize_text(text, w):
  if len(text) > w:
    text = text[:w//2-2] + '...' + text[-w//2+1:]
  return text


class Formatter:

  iolock = threading.RLock()

  def __init__(self, actions, verbose=False):
    self.actions = actions
    self.verbose = verbose
    self.prefix, self.sep, self.end = ('', ' ', '\n') if verbose else ('\r', '', '')
    self.num_announced = 0

  def announce_execute(self, action):
    with self.iolock:
      self.num_announced += 1
      width = tty.terminal_size()[0]
      line = self.prefix + tty.colored(
        '({}/{}) [{}]:'.format(self.num_announced, len(self.actions), action.long_name),
        'cyan'
      ) + ' '
      line += tty.colored(ellipsize_text(action.get_display(), width-len(line)), 'yellow')
      tty.clear_line()
      print(line, sep=self.sep, end=self.end)

  def announce_finished(self, action):
    if not action.progress.buffer_has_content():
      return
    with self.iolock:
      if not self.verbose:
        tty.clear_line()
      line = tty.colored('[{}]:'.format(action.long_name), 'magenta')
      line += ' ' + tty.colored(action.get_display(), 'yellow')
      print(line)
      action.progress.print_buffer()

  def announce_failure(self, action):
    with self.iolock:
      if not self.verbose:
        tty.clear_line()
      line = tty.colored('[{} FAILED with {}]:'.format(action.long_name, action.progress.code), 'red', 'white')
      line += ' ' + tty.colored(action.get_display(), 'yellow')
      print(line)
      action.progress.print_buffer()


class ParallelExecutor:

  def __init__(self, max_workers, formatter):
    self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    self.formatter = formatter
    self.consolelock = threading.RLock()
    self.datalock = threading.RLock()
    self.action_completed = threading.Condition()
    self.visited = []
    self.futures = []

  def __enter__(self):
    self.pool.__enter__()
    return self

  def __exit__(self, *args):
    return self.pool.__exit__(*args)

  def put(self, action):
    with self.datalock:
      self.visited.append(action)
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

  def _worker(self, action):
    try:
      console = not action.target.console
      action.progress = ActionProgress(do_buffering=console)
      self._wait_for_deps(action)
      for dep in action.all_deps():
        if dep.progress.code != 0:
          action.skip()
          return action  # action skipped because of errored dependency
      if console:
        with self.consolelock:
          self.formatter.announce_execute(action)
          action.execute()
      else:
        self.announce_execute(action)
        action.execute()
      return action
    except:
      traceback.print_exc()
      action.progress.executed = True
      action.progress.code = 1
      raise
    finally:
      with self.action_completed:
        self.action_completed.notify_all()

  def _wait_for_deps(self, action):
    def all_deps_executed():
      for dep in action.deps:
        if not dep.is_executed():
          return False
      return True
    while not all_deps_executed():
      with self.action_completed:
        self.action_completed.wait()

  def wait(self):
    self.pool.shutdown(wait=True)


def _execute_action(action):
  progress = ActionProgress(do_buffering=action.console)


def build_argparser(parser):
  parser.add_argument('targets', nargs='*', metavar='TARGET')
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('-j', '--jobs', type=int, default=cpu_count() * 2)


def build_main(args, session, module):
  # Execute the module.
  require.context.load_module(module)

  # Generate the action graph.
  targets = session.resolve_targets(args.targets) if args.targets else None
  actions = list(session.build_target_graph().translate(targets).topo_sort())
  iter_actions = iter(actions)

  formatter = Formatter(actions, verbose=args.verbose)
  with ParallelExecutor(max_workers=args.jobs, formatter=formatter) as executor:
    while iter_actions or executor.futures:
      for action in (f.result() for f in executor.pop_done()):
        if action.skipped: continue
        if action.progress.code != 0:
          formatter.announce_failure(action)
          return action.progress.code
        formatter.announce_finished(action)
      if iter_actions:
        action = next(iter_actions, None)
        if action is None:
          iter_actions = None
        elif not action.is_skippable():
          executor.put(action)
      else:
        executor.wait()

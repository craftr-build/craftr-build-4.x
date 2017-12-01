"""
The default, Python-based build backend.
"""

import concurrent.futures
import json
import threading
import traceback
import sys
import craftr from '../public'
import {path, sh, tty} from '../utils'
import {BuildBackend} from '.'
import {ActionProgress, Null as NullAction} from '../core/actions'

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
      text = action.get_display()
      if not self.verbose:
        text = ellipsize_text(text, width-len(line))
      line += tty.colored(text, 'yellow')
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
      line = tty.colored('[{}]:'.format(action.long_name), 'red')
      line += ' ' + tty.colored(action.get_display(), 'yellow') + '\n'
      print(line)
      action.progress.print_buffer()
      print(tty.colored('Failed with exit-code {}\n'.format(action.progress.code), 'red'))


class ParallelExecutor:

  def __init__(self, max_workers, formatter):
    self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    self.formatter = formatter
    self.consolelock = threading.RLock()
    self.datalock = threading.RLock()
    self.action_completed = threading.Condition()
    self.futures = []
    self.on_finished = None

  def __enter__(self):
    self.pool.__enter__()
    return self

  def __exit__(self, *args):
    return self.pool.__exit__(*args)

  def put(self, action):
    with self.datalock:
      future = self.pool.submit(self._worker, action)
      future.action = action
      self.futures.append(future)

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
      if action.is_skippable():
        action.skip()
        return action
      if console:
        with self.consolelock:
          self.formatter.announce_execute(action)
          action.execute()
      else:
        self.formatter.announce_execute(action)
        action.execute()
      return action
    except:
      traceback.print_exc()
      action.progress.abort()
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

  def abort_all(self):
    #self.pool.shutdown(wait=False)
    with self.datalock:
      futures, self.futures = self.futures, []
    for future in self.futures:
      progress = future.action.progress
      if progress:
        progress.abort()

  def run(self, actions):
    actions = iter(actions)
    try:
      with self:
        while actions or self.futures:
          for action in (f.action for f in self.pop_done()):
            action.save_hash()
            if action.skipped: continue
            if action.progress.code != 0:
              self.formatter.announce_failure(action)
              return action.progress.code
            self.formatter.announce_finished(action)
            if self.on_finished:
              try:
                self.on_finished(action)
              except:
                traceback.print_exc()
          if actions:
            action = next(actions, None)
            if action is None:
              actions = None
            else:
              self.put(action)
    except:
      self.abort_all()
      raise


class DefaultBuildBackend(BuildBackend):

  CACHE_FILENAME = '.config/default_backend_cache.json'

  def init_backend(self, session):
    pass

  def build_parser(self, session, parser):
    parser.add_argument('targets', nargs='*', metavar='TARGET')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-j', '--jobs', type=int, default=cpu_count() * 2)
    parser.add_argument('--dotviz-targets', action='store_true')
    parser.add_argument('--dotviz-actions', action='store_true')

  def run(self, session, module, args):
    # Execute the module.
    session.load_main(module)

    # Resolve targets and parse additional command-line arguments for the targets.
    targets = []
    target_args = {}
    for target_name in args.targets:
      name, target_args = target_name.partition('=')[::2]
      target_args = sh.split(target_args)
      target = session.resolve_target(name)
      if target_args and not isinstance(target.data, craftr.Gentarget):
        tn = type(target.data).__name__
        print('fatal: additional command-line arguments are only supported\n'
              '       for gentarget()s ({} is a {})'.format(name, tn))
        return 1
      if target_args:
        target.data.add_additional_args(target_args)
      targets.append(target)

    # Generate the action graph.
    tg = session.build_target_graph()
    if args.dotviz_targets:
      tg.dotviz(sys.stdout)
      return 0
    tg.complete()
    ag = tg.translate(targets or None)
    if args.dotviz_actions:
      ag.dotviz(sys.stdout)
      return 0
    actions = [x for x in ag.topo_sort() if not isinstance(x, NullAction)]

    formatter = Formatter(actions, verbose=args.verbose)
    executor = ParallelExecutor(max_workers=args.jobs, formatter=formatter)
    try:
      return executor.run(actions)
    except KeyboardInterrupt:
      print('keyboard interrupt')
      return 1
    return 0


module.exports = DefaultBuildBackend

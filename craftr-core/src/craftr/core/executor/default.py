
"""
A very simple, sequential executor.
"""

import typing as t
from craftr.core.actions.action import ActionContext

from craftr.core.executor.api import IExecutor
from craftr.core.task import Task

if t.TYPE_CHECKING:
  from .graph import ExecutionGraph
  from craftr.core.settings import Settings


class DefaultExecutor(IExecutor):

  def __init__(self, verbose: bool = False) -> None:
    self._verbose = verbose

  @classmethod
  def from_settings(cls, settings: 'Settings') -> 'DefaultExecutor':
    return cls(settings.get_bool('core.verbose', False))

  def execute(self, graph: 'ExecutionGraph') -> None:
    outdated_tasks: t.Set[Task] = set()
    context = ActionContext(verbose=self._verbose)
    for task in graph.get_ordered_tasks():
      if task.is_outdated() or any(x in outdated_tasks for x in task.get_dependencies()):
        outdated_tasks.add(task)
        print('> Task', task.path, flush=True)
        actions = task.do_first_actions + task.get_actions() + task.do_last_actions
        for action in actions:
          action.execute(context)
        task.completed()
      else:
        print('> Task', task.path, 'UP TO DATE', flush=True)


"""
A very simple, sequential executor.
"""

import typing as t

from craftr.core.executor.api import Executor
from craftr.core.task import Task

if t.TYPE_CHECKING:
  from .graph import ExecutionGraph


class DefaultExecutor(Executor):

  def execute(self, graph: 'ExecutionGraph') -> None:
    outdated_tasks: t.Set[Task] = set()
    for task in graph.get_ordered_tasks():
      if task.is_outdated() or any(x in outdated_tasks for x in task.get_dependencies()):
        outdated_tasks.add(task)
        print('> Task', task.path)
        actions = task.get_actions()
        for action in actions:
          action.execute()
        task.completed()
      else:
        print('> Task', task.path, 'UP TO DATE')


"""
A very simple, sequential executor.
"""

import typing as t

from kahmi.core.executor.api import Executor
from kahmi.core.system.task import Task
from kahmi.core.system.taskstate import calculate_task_hash

if t.TYPE_CHECKING:
  from kahmi.core.system.executiongraph import ExecutionGraph
  from kahmi.core.util.config import Config


class SimpleExecutor(Executor):

  def __init__(self, config: 'Config') -> None:
    pass  # don't need the config

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

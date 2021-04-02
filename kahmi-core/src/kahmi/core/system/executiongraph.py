
import typing as t

from kahmi.core.system.task import Task
from kahmi.core.util.preconditions import check_argument


class ExecutionGraph:
  """
  The execution graph contains a plan for the order in which tasks need to be executed. It is
  accessible via the #Context.graph property, but it will be empty until all projects have
  been evaluated and #Context.execute() is called.

  The execution graph contains only those tasks that are selected for execution. Some tasks may
  not be included by default (if #Task.default is set to `False`) or are skipped because they
  have not been explicitly selected.
  """

  def __init__(self):
    self._ready = False
    self._tasks: t.Dict[str, Task] = {}
    self._when_ready_callbacks: t.List[t.Callable[[ExecutionGraph], None]] = []

  def when_ready(self, closure: t.Callable[['ExecutionGraph'], None]) -> None:
    """
    Adds a callback that is invoked when the execution graph is ready. If the graph is ready
    by the time this method is called, the *closure* is invoked immediately.
    """

    if self._ready:
      closure(self)
    else:
      self._when_ready_callbacks.append(closure)

  def is_ready(self) -> bool:
    return self._ready

  def ready(self) -> bool:
    """ Declare that the execution graph is ready. Invokes registered listeners. """

    if not self._ready:
      self._ready = True
      for closure in self._when_ready_callbacks:
        closure(self)

  def add_task(self, task: Task) -> None:
    """ Add a task and all it's dependencies to the graph. """

    if not self._check_contains(task):
      self._tasks[task.path] = task

    for dependency in task.get_dependencies():
      self.add_task(dependency)

  def add_tasks(self, tasks: t.Iterable[Task]) -> None:
    for task in tasks:
      self.add_task(task)

  def has_task(self, task: t.Union[str, Task]) -> bool:
    """
    Returns `True` if the specified *task* (either the _absolute_ path of the task or the #Task
    instance itself) is contained in the execution graph.
    """

    if isinstance(task, str):
      return task in self._tasks
    return self._check_contains(task)

  def _check_contains(self, task: Task) -> bool:
    if task.path in self._tasks:
      check_argument(task is self._tasks[task.path], f'same path different task instance: {task.path!r}')
      return True
    return False

  def get_ordered_tasks(self) -> t.List[Task]:
    """
    Retrieve the tasks of the execution graph in the order that they need to be executed.
    """

    result: t.List[Task] = []

    def add(task: Task, seen: t.Set[Task]) -> None:
      if not self._check_contains(task):
        return
      if task in seen:
        raise RuntimeError(f'cyclic dependency graph involving task {task.path!r}')
      seen.add(task)
      for dep in task.get_dependencies():
        add(dep, seen)
      if task not in result:
        result.append(task)

    for task in self._tasks.values():
      add(task, set())

    return result

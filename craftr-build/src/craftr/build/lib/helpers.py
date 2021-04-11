
import weakref
import types
import typing as t
from craftr.core.closure import Closure
from craftr.core.project import Project
from craftr.core.project.project import ExtensibleObject
from craftr.core.task import Task
from craftr.core.util.preconditions import check_not_none

T = t.TypeVar('T')
T_Task = t.TypeVar('T_Task', bound=Task)


class _Namespace(ExtensibleObject):

  def __init__(self, name: str) -> None:
    super().__init__()
    self._name = name

  def __repr__(self) -> str:
    return f'_Namespace(name={self._name!r})'


class TaskFactoryExtension(t.Generic[T_Task]):
  """
  This is a helper class that wraps a #Task subclass to act as a factory for that class. It is used
  as a convenience when registering a task as an extension to a #Project such that it can be used
  to define a default task as well as defining a custom named task of the type.

  ```py
  def apply(project: Project, name: str) -> None:
    project.register_extension('myTaskType', TaskFactoryExtension(project, 'myTaskType', MyTaskType))
  ```

  Inside a project, the task can then be instantiated with a configuration closure, and optionally
  with a custom task name.

  ```py
  myTaskType {
    # ...
  }
  myTaskType('otherTaskName') {
    # ...
  }

  assert 'myTaskType' in tasks
  assert 'otherTaskName' in tasks
  ```
  """

  def __init__(self, project: Project, default_name: str, task_type: t.Type[T_Task]) -> None:
    self._project = weakref.ref(project)
    self._default_name = default_name
    self._task_type = task_type

  def __repr__(self) -> str:
    return f'TaskFactoryExtension(project={self._project()}, type={self._task_type})'

  @property
  def project(self) -> Project:
    return check_not_none(self._project(), 'lost project reference')

  @property
  def type(self) -> t.Type[T_Task]:
    return self._task_type

  def __call__(self, arg: t.Union[str, Closure] = None) -> T_Task:
    """
    Create a new instance of the task type. If a string is specified, it will be used as the task
    name. If a closure is specified, the default task name will be used and the task will be
    configured with the closure.
    """

    project = check_not_none(self._project(), 'lost project reference')
    if isinstance(arg, str):
      task = project.task(arg or self._default_name, self._task_type)
    else:
      task = project.task(self._default_name, self._task_type)
      task.configure(arg)
    return task


class PluginRegistration:
  """
  Utility class to register classes and functions using decorators and later export them into a
  project when your plugin is applied to a project.

  ```py
  from craftr.build.lib import PluginRegistration
  from craftr.core.task import Task

  plugin = PluginRegistration()
  apply = plugin.apply

  @plugin.exports
  class MyCustomTask(Task):
    # ...
  ```
  """

  def __init__(self) -> None:
    self._exports: t.Dict[str, t.Any] = {}

  def exports(self, value: T, name: t.Optional[str] = None) -> T:
    if name is None:
      if isinstance(value, type) or isinstance(value, types.FunctionType):
        name = value.__name__
      else:
        raise ValueError(f'unable to derive name from value of type {type(value).__name__}')
    self._exports[name] = value
    return value

  def build_namespace(self, project: Project, name: str) -> t.Any:
    obj = _Namespace(name)
    for key, value in self._exports.items():
      if isinstance(value, type) and issubclass(value, Task):
        # TODO(nrosenstein): Better default task name?
        obj.add_extension(key, TaskFactoryExtension(project, key, value))
      else:
        obj.add_extension(key, value)
    return obj

  def apply(self, project: Project, name: str) -> None:
    project.add_extension(name, self.build_namespace(project, name))

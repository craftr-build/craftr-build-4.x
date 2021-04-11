
import glob
import string
import typing as t
import weakref
from pathlib import Path
from craftr.core.closure import Closure

from craftr.core.closure import IConfigurable
from craftr.core.task import Task
from craftr.core.util.preconditions import check_not_none

if t.TYPE_CHECKING:
  from craftr.core.context import Context

T_Task = t.TypeVar('T_Task', bound='Task')


class ExtensibleObject:

  def __init__(self) -> None:
    self._extensions: t.Dict[str, t.Any] = {}

  def __getattr__(self, key: t.Any) -> t.Any:
    try:
      return object.__getattribute__(self, '_extensions')[key]
    except KeyError:
      raise AttributeError(f'{self} has no attribute or extension named "{key}".')

  def add_extension(self, key: str, extension: t.Any) -> None:
    self._extensions[key] = extension


class Project(ExtensibleObject):
  """
  A project is a collection of tasks, usually populated through a build script, tied to a
  directory. Projects can have sub projects and there is usually only one root project in
  build.
  """

  def __init__(self,
    context: 'Context',
    parent: t.Optional['Project'],
    directory: t.Union[str, Path],
  ) -> None:
    super().__init__()
    self._context = weakref.ref(context)
    self._parent = weakref.ref(parent) if parent is not None else parent
    self.directory = Path(directory)
    self._name: t.Optional[str] = None
    self._build_directory: t.Optional[Path] = None
    self._tasks: t.Dict[str, 'Task'] = {}
    self._subprojects: t.Dict[str, 'Project'] = {}

  def __repr__(self) -> str:
    return f'Project("{self.name}")'

  @property
  def context(self) -> 'Context':
    return check_not_none(self._context(), 'lost reference to context')

  @property
  def parent(self) -> t.Optional['Project']:
    if self._parent is not None:
      return check_not_none(self._parent(), 'lost reference to parent')
    return None

  @property
  def name(self) -> str:
    if self._name is not None:
      return self._name
    return self.directory.name

  @name.setter
  def name(self, name: str) -> None:
    if set(name) - set(string.ascii_letters + string.digits + '_-'):
      raise ValueError(f'invalid task name: {name!r}')
    self._name = name

  @property
  def path(self) -> str:
    parent = self.parent
    if parent is None:
      return self.name
    return f'{parent.path}:{self.name}'

  @property
  def build_directory(self) -> Path:
    if self._build_directory:
      return self._build_directory
    return self.context.get_default_build_directory(self)

  @build_directory.setter
  def build_directory(self, path: t.Union[str, Path]) -> None:
    self._build_directory = Path(path)

  def task(self, name: str, task_class: t.Optional[t.Type[T_Task]] = None) -> T_Task:
    """
    Create a new task of type *task_class* (defaulting to #Task) and add it to the project. The
    task name must be unique within the project.
    """

    if name in self._tasks:
      raise ValueError(f'task name already used: {name!r}')

    task = (task_class or Task)(self, name)
    self._tasks[name] = task
    return t.cast(T_Task, task)

  @property
  def tasks(self) -> 'TaskContainer':
    """ Returns the #TaskContainer object for this project. """

    return TaskContainer(self._tasks)

  def subproject(self, directory: str) -> 'Project':
    """
    Reference a subproject by a path relative to the project directory. If the project has not
    been loaded yet, it will be created and initialized.
    """

    directory = str(self.directory.joinpath(directory).resolve())

    if directory not in self._subprojects:
      project = Project(self.context, self, directory)
      self.context.initialize_project(project)
      self._subprojects[directory] = project

    return self._subprojects[directory]

  def get_subproject_by_name(self, name: str) -> 'Project':
    """
    Returns a sub project of this project by it's name. Raises a #ValueError if no sub project
    with the specified name exists in the project.
    """

    for project in self._subprojects.values():
      if project.name == name:
        return project

    raise ValueError(f'project {self.path}:{name} does not exist')

  @t.overload
  def subprojects(self) -> t.List['Project']:
    """ Returns a list of the project's loaded subprojects. """

  @t.overload
  def subprojects(self, closure: t.Callable[['Project'], None]) -> None:
    """ Call *closure* for every subproject currently loaded in the project.. """

  def subprojects(self, closure = None):
    if closure is None:
      return list(self._subprojects.values())
    else:
      for subproject in self._subprojects.values():
        closure(subproject)

  def apply(self, plugin_name: str) -> None:
    """
    Loads a plugin and applies it to the project. Plugins are loaded via #Context.plugin_loader
    and applied to the project immediately after. The default implementation for loading plugins
    uses Python package entrypoints.
    """

    plugin = self.context.plugin_loader.load_plugin(plugin_name)
    plugin.apply(self)

  def file(self, sub_path: str) -> Path:
    return self.directory / sub_path

  def glob(self, pattern: str) -> t.List[str]:
    """
    Apply the specified glob pattern relative to the project directory and return a list of the
    matched files.
    """

    return glob.glob(str(self.directory / pattern))

  def add_task_extension(self, name: str, task_type: t.Type[T_Task], default_name: t.Optional[str] = None) -> None:
    self.add_extension(name, _TaskExtensionWrapper(self, default_name or name, task_type))


class _TaskExtensionWrapper(t.Generic[T_Task]):
  """
  Helper class that wraps a #Task subclass, returning an instance of the class when calling the
  object or creating a new instance and configuring it when #configure() is called.

  We do this to simplify the use of the Python API and Craftr DSL:

  Python API:

  ```py
  my_extension = project.my_extension()  # Invokes ConfigurableWrapper.__call__()
  # ...
  ```

  Craftr DSL:

  ```py
  my_extension {  # Invokes ConfigurableWrapper.configure()
    # ...
  }
  ```
  """

  def __init__(self, project: 'Project', default_name: str, task_type: t.Type[T_Task]) -> None:
    self._project = weakref.ref(project)
    self._default_name = default_name
    self._task_type = task_type

  def __repr__(self) -> str:
    return f'_TaskExtensionWrapper({self._task_type})'

  def __call__(self, arg: t.Union[str, 'Closure'] = None) -> T_Task:
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

  # TODO(NiklasRosenstein): We only need configure() once we figured out how to distinguish between
  #   configure calls in DSL and propagate it to the transpiler as well as the runtime.

  #def configure(self, closure: 'Closure') -> T_Task:
  #  task = self()
  #  task.configure(closure)
  #  return task


class TaskContainer(IConfigurable):

  def __init__(self, tasks: t.Dict[str, 'Task']) -> None:
    self._tasks = tasks

  def __iter__(self):
    return iter(self._tasks.values())

  def configure(self, closure: 'Closure') -> None:
    for task in self._tasks.values():
      task.configure(closure)

  def __getattr__(self, key: str) -> 'Task':
    return self._tasks[key]

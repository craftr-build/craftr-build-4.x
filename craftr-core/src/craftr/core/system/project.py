
import string
import typing as t
import weakref
from pathlib import Path

from craftr.core.util.preconditions import check_not_none

if t.TYPE_CHECKING:
  from craftr.core.system.context import Context
  from craftr.core.system.task import Task

T_Task = t.TypeVar('T_Task', bound='Task')


class Project:
  """
  A project is a collection of tasks, usually populated through a build script, tied to a
  directory. Projects can have sub projects and there is usually only one root project in
  build.
  """

  def __init__(self,
    context: 'Context',
    parent: t.Optional['Project'],
    directory: str,
  ) -> None:
    self._context = weakref.ref(context)
    self._parent = weakref.ref(parent) if parent is not None else parent
    self.directory = Path(directory)
    self._name: t.Optional[str] = None
    self._build_directory: t.Optional[Path] = None
    self._tasks: t.Dict[str, 'Task'] = {}
    self._subprojects: t.Dict[str, 'Project'] = {}

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

  # TODO(NiklasRosenstein): Setter for build_directory

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

  @t.overload
  def tasks(self) -> t.List['Task']:
    """ Return a list of the project's tasks. """

  @t.overload
  def tasks(self, closure: t.Callable[['Task'], None]) -> None:
    """ Call *closure* for every task. """

  def tasks(self, closure = None):
    if closure is None:
      return list(self._tasks.values())
    else:
      for task in self._tasks.values():
        closure(task)

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

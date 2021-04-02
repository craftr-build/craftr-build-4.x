
import enum
import typing as t
import weakref

from nr.caching.api import KeyDoesNotExist

from craftr.core.property import HavingProperties, collect_properties
from craftr.core.system.extension import IConfigurable
from craftr.core.system.taskstate import calculate_task_hash
from craftr.core.util.collections import unique
from craftr.core.util.preconditions import check_not_none

if t.TYPE_CHECKING:
  from craftr.core.actions import Action
  from craftr.core.system.project import Project

TASK_HASH_NAMESPACE = 'task-hashes'


class TaskPropertyType(enum.Enum):
  Input = enum.auto()
  Output = enum.auto()


class Task(HavingProperties, IConfigurable):
  """
  A task represents a set of sequential actions that are configurable through properties and may
  have dependencies on other tasks. Using the property system, dependencies between tasks can be
  computed automatically without having to explicitly list the dependencies.

  Tasks are rendered into executable #BuildNode objects to construct the #BuildGraph.
  """

  Input = TaskPropertyType.Input
  Output = TaskPropertyType.Output

  #: Explicit dependencies of the task. Tasks in this list will always be executed before
  #: this task.
  dependencies: t.List['Task']

  #: Whether the task should be included if no explicit set of tasks is selected for execution.
  #: This is `True` by default for all tasks (but can be overwritten by subclasses).
  default: bool = True

  #: A short description of the task.
  description: t.Optional[str] = None

  #: A name for the group that the task belongs to. Task groups are used to select tasks via
  #: common identifiers (e.g. `run`, `compile` or `debug` are generic terms that could apply to
  #: a variety of tasks).
  group: t.Optional[str] = None

  #: A boolean flag that indicates whether the task is always to be considered outdated.
  always_outdated: bool = False

  def __init__(self, project: 'Project', name: str) -> None:
    super().__init__()
    self._project = weakref.ref(project)
    self._name = name
    self.dependencies = []

  def __repr__(self) -> str:
    return f'{type(self).__name__}({self.path!r})'

  @property
  def project(self) -> 'Project':
    return check_not_none(self._project(), 'lost reference to project')

  @property
  def name(self) -> str:
    return self._name

  @property
  def path(self) -> str:
    return f'{self.project.path}:{self.name}'

  def get_dependencies(self) -> t.List['Task']:
    """ Get all dependencies of the task, including those inherited through properties. """

    dependencies = self.dependencies[:]

    for prop in self.get_properties().values():
      if TaskPropertyType.Output not in prop.annotations:
        dependencies.extend(p.origin for p in collect_properties(prop)
            if isinstance(p.origin, Task))

    dependencies = list(unique(dependencies))

    try:
      dependencies.remove(self)
    except ValueError:
      pass

    return dependencies

  def get_actions(self) -> t.List['Action']:
    """ Get the list of actions for this task. This should be called when everything is loaded. """

    raise NotImplementedError(f'{type(self).__name__}.get_actions()')

  def is_outdated(self) -> bool:
    """
    Checks if the task is outdated.
    """

    if self.always_outdated:
      return True

    # TODO(NiklasRosenstein): If the task has no input file properties or does not produce output
    #   files should always be considered as outdated.

    hash_value = calculate_task_hash(self)

    try:
      stored_hash = self.project.context.metadata_store.\
          namespace(TASK_HASH_NAMESPACE).load(self.path).decode()
    except KeyDoesNotExist:
      stored_hash = None

    return hash_value != stored_hash

  def completed(self) -> None:
    """
    Called when the task was executed.
    """

    if not self.always_outdated:
      self.project.context.metadata_store.\
          namespace(TASK_HASH_NAMESPACE).store(self.path, calculate_task_hash(self).encode())

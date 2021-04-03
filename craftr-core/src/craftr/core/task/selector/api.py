
import abc
import typing as t

if t.TYPE_CHECKING:
  from craftr.core.project import Project
  from craftr.core.task import Task


@t.runtime_checkable
class ITaskSelector(t.Protocol, metaclass=abc.ABCMeta):
  """ An interface to expand a string into a set of tasks in the context of a project. """

  @abc.abstractmethod
  def select_tasks(self, selection: str, project: 'Project') -> t.Collection['Task']:
    pass

  @abc.abstractmethod
  def select_default(self, project: 'Project') -> t.Collection['Task']:
    pass

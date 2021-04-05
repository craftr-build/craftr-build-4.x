
import abc
import typing as t
from pathlib import Path


if t.TYPE_CHECKING:
  from craftr.core.context import Context
  from craftr.core.project import Project


@t.runtime_checkable
class IProjectLoader(t.Protocol, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def load_project(self, context: 'Context', parent: t.Optional['Project'], path: Path) -> 'Project':
    pass

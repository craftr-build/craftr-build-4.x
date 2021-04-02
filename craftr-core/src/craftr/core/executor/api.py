
import abc
import typing as t

if t.TYPE_CHECKING:
  from craftr.core.system.executiongraph import ExecutionGraph


class Executor(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def execute(self, graph: 'ExecutionGraph') -> None:
    pass

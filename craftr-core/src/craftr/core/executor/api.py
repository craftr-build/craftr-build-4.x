
import abc
import typing as t

if t.TYPE_CHECKING:
  from .graph import ExecutionGraph


class Executor(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def execute(self, graph: 'ExecutionGraph') -> None:
    pass

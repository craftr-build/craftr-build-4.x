
import abc
import typing as t

if t.TYPE_CHECKING:
  from .graph import ExecutionGraph


@t.runtime_checkable
class IExecutor(t.Protocol):

  def execute(self, graph: 'ExecutionGraph') -> None:
    raise NotImplementedError


import abc
import typing as t

if t.TYPE_CHECKING:
  from craftr.core.system.executiongraph import ExecutionGraph
  from craftr.core.util.config import Config


class Executor(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def __init__(self, config: 'Config') -> None:
    pass

  @abc.abstractmethod
  def execute(self, graph: 'ExecutionGraph') -> None:
    pass

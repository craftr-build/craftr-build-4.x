
import typing as t


Closure = t.Callable[[t.Any], t.Any]


class Configurable(t.Protocol):
  """
  Abstract base class for objects configurable through closures. Basically they are
  """

  def __call__(self, closure: Closure) -> t.Any:
    raise NotImplementedError(f'{type(self).__name__}.__call__() is not implemented')

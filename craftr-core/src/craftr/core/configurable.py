
import typing as t

T = t.TypeVar('T')
U = t.TypeVar('U')


@t.runtime_checkable
class Closure(t.Protocol[T, U]):
  def __call__(self, val: T) -> U:
    raise NotImplementedError(f'{type(self).__name__}.__call__() is not implemented')


class Configurable(t.Protocol[T, U]):
  """
  Abstract base class for objects configurable through closures. Basically they are
  """

  def __call__(self, closure: Closure[T, t.Any]) -> U:
    raise NotImplementedError(f'{type(self).__name__}.__call__() is not implemented')

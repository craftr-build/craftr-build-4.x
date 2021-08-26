
import abc
import enum
import sys
import types
import typing as t

T = t.TypeVar('T')


class Configurable(abc.ABC):
  """
  Abstract base class for closure configurables. If an instance of a subclass of #Configurable is the
  delegate of a #Closure, it's #__configure__() method will be called which allows the configurable to
  implement a surrogate delegate or invoke the closure's backing function multiple times.
  """

  @abc.abstractmethod
  def __configure__(self, dispatch: t.Callable[[t.Any], t.Any]) -> t.Any: ...


class Closure:
  """
  Closures are functions that take at least one argument: A #ClosureContextProxy object. Using the context proxy,
  the function may use it to dynamically resolve variables in the closure's extended scope, which is composed of

  * An owner object (usually another closure)
  * A delegate object

  The delegate is usually the target of the #ClosureContextProxy unless the delegate is a #Configurable object or
  a callable, in which case the #Configurable.__configure__() method or the callable can decide the proxy target.
  """

  def __init__(self,
    func: t.Callable,
    owner: t.Any,
    delegate: t.Optional[t.Any],
    args: t.Optional[t.List[t.Any]] = None,
    kwargs: t.Optional[t.Mapping[str, t.Any]] = None,
  ) -> None:
    self.func = func
    self.owner = owner
    self.delegate = delegate
    self.args = args or []
    self.kwargs = kwargs or {}

  def __call__(self, *args, **kwargs) -> t.Any:
    """ Invokes the closure with the specified arguments. """

    def invoke(delegate: t.Any) -> t.Any:
      return self.func(ClosureContextProxy(self, delegate), *self.args, *args, **{**self.kwargs, **kwargs})

    if self.delegate is not None and hasattr(self.delegate, '__configure__'):
      return t.cast(Configurable, self.delegate).__configure__(invoke)
    elif self.delegate is not None and callable(self.delegate):
      return self.delegate(invoke)

    return invoke(self.delegate)

  def apply(self, delegate: t.Optional[t.Any], *args, **kwargs) -> t.Any:
    """ Set the closure's delegate and invoke it with the specified arguments. """

    self.delegate = delegate
    return self(*args, **kwargs)

  def curry(self, *args, **kwargs) -> 'Closure':
    """ Return a copy of the closure with the specified arguments curried. """

    return Closure(self.func, self.owner, self.delegate, self.args + list(args), {**self.kwargs, **kwargs})


class ClosureContextProxy:

  def __init__(self, closure: Closure, target: t.Any) -> None:
    self.__closure__ = closure
    self.__target__ = target

  def __repr__(self) -> str:
    return f'ClosureContextProxy(closure={self.__closure__})'

  def __call__(self) -> t.Any:
    return self.__target__

  def __getattr__(self, name: str) -> t.Any:
    return getattr(self.__target__, name)

  def __setattr__(self, name: str, value: t.Any) -> None:
    if name == '__closure__' or name == '__target__':
      object.__setattr__(self, name, value)
    else:
      setattr(self.__target__, name, value)


def closure(owner: t.Optional[t.Any] = None, delegate: t.Optional[t.Any] = None) -> t.Callable[[t.Callable], Closure]:
  """
  Decorator for closure functions.
  """

  frame = sys._getframe(1)

  try:
    def decorator(func: t.Callable) -> Closure:
      return Closure(func, owner, delegate)

    return decorator
  finally:
    del frame


"""
Provides the #Closure type that is heavily inspired by Groovy.
"""

import builtins
import enum
import sys
import types
import typing as t

from craftr.core.util.preconditions import check_instance_of

T = t.TypeVar('T')
T_IConfigurable = t.TypeVar('T_IConfigurable', bound='IConfigurable')


class _ValueRef:

  def __init__(self, get: t.Callable[[], t.Any], set: t.Callable[[t.Any], None], info: t.Callable[[], str]) -> None:
    self.get = get
    self.set = set
    self.info = info

  def __repr__(self) -> str:
    return f'_ValueRef({self.info()})'

  @classmethod
  def attr(cls, obj: t.Any, key: str) -> '_ValueRef':
    def setter(v):
      # Do not allow overriding a function/method of the class.
      has_value = getattr(type(obj), key, None)
      if isinstance(has_value, (types.FunctionType, types.MethodType)):
        raise RuntimeError(f'cannot set function/method')
      setattr(obj, key, v)
    return _ValueRef(lambda: getattr(obj, key), setter, lambda: f'attr {key!r} of {obj!r}')

  @classmethod
  def dict(cls, dct: t.Dict[str, t.Any], key: str) -> '_ValueRef':
    return _ValueRef(lambda: dct[key], lambda v: dct.__setitem__(key, v), lambda: f'key {key!r} of {dct!r}')

  @classmethod
  def frame_locals(cls, frame: types.FrameType, key: str) -> '_ValueRef':
    # TODO(NiklasRosenstein): Figure out a clever way to set local variable in a frame?
    #   Writing into f_locals does not actually work because in optimized function code,
    #   local variables are stored "fast" using an internal array and f_locals is just a
    #   copy of those locals as a dictionary.
    def setter(_v):
      raise RuntimeError('setting outter local variable from Closure is not supported. '
          'Use the `nonlocal` keyword.')
    return _ValueRef(lambda: frame.f_locals[key], setter, lambda: f'{key!r} of locals')

  @classmethod
  def frame_globals(cls, frame: types.FrameType, key: str) -> '_ValueRef':
    def setter(_v):
      raise RuntimeError('setting globals from inside a Closure is not supported')
    return _ValueRef(lambda: frame.f_globals[key], setter, lambda: f'{key!r} of globals')

  @classmethod
  def builtin(cls, key: str) -> '_ValueRef':
    def setter(_v):
      raise RuntimeError('setting builtins is not supported')
    return _ValueRef(lambda: getattr(builtins, key), setter, lambda: f'{key!r} of builtins')


class ResolveStrategy(enum.Enum):
  OWNER_FIRST = enum.auto()
  DELEGATE_FIRST = enum.auto()


class Closure:
  """
  Closures are functions that take at least one argument: The #Closure object itself. Using the
  closure object, the function may use it to dynamically resolve variables in the closure's
  extended scope, which is composed of

  * The locals of the stackframe where it was defined
  * An owner object (usually another closure)
  * A delegate object

  The delegate of a closure can be modified dynamically. Resolving a variable through the
  Closure's #__getitem__() will check the delegate or owner first (depending on the
  #ResolveStrategy) and the the locals of the other stackframe. (Default is
  #ResolveStrategy.OWNER_FIRST).
  """

  def __init__(self,
    func: t.Callable,
    stackframe: t.Optional[types.FrameType],
    owner: t.Any,
    delegate: t.Optional[t.Any],
    resolve_strategy: t.Union[str, ResolveStrategy] = ResolveStrategy.DELEGATE_FIRST,
    args: t.Optional[t.List[t.Any]] = None,
    kwargs: t.Optional[t.Mapping[str, t.Any]] = None,
  ) -> None:
    self.func = func
    self.stackframe = stackframe
    self.owner = owner
    self.delegate = delegate
    self.resolve_strategy = ResolveStrategy[resolve_strategy] if isinstance(resolve_strategy, str) else resolve_strategy
    self.args = args or []
    self.kwargs = kwargs or {}
    self.locals: t.Dict[str, t.Any] = {}

  @property
  def resolve_strategy(self) -> ResolveStrategy:
    return self._resolve_strategy

  @resolve_strategy.setter
  def resolve_strategy(self, strategy: t.Union[str, ResolveStrategy]) -> None:
    if isinstance(strategy, str):
      strategy = ResolveStrategy[strategy]
    check_instance_of(strategy, ResolveStrategy)
    self._resolve_strategy = strategy

  @property
  def __closure__(self) -> t.Any:
    return self.func.__closure__  # type: ignore

  def __call__(self, *args, **kwargs) -> t.Any:
    """ Invokes the closure with the specified arguments. """

    return self.func(self, *self.args, *args, **{**self.kwargs, **kwargs})

  def apply(self, delegate: t.Optional[t.Any], *args, **kwargs) -> t.Any:
    """ Set the closure's delegate and invoke it with the specified arguments. """

    self.delegate = delegate
    return self(*args, **kwargs)

  def with_locals(self, **kwargs) -> 'Closure':
    """ Modifies the closure object to update the #locals and returns `self`. """

    self.locals.update(kwargs)
    return self

  def curry(self, *args, **kwargs) -> 'Closure':
    """ Return a copy of the closure with the specified arguments curried. """

    return Closure(self.func, self.stackframe, self.owner, self.delegate, self.resolve_strategy,
      self.args + list(args), {**self.kwargs, **kwargs})

  def __getitem__(self, key: str) -> t.Any:
    """
    Resolve the variable name *key* in the Closure's owner, delegate and locals of it's
    associated stackframe according to it's resolve strategy.
    """

    return self._resolve(key).get()

  def __setitem__(self, key: str, value: t.Any) -> None:
    """
    Set a variable with the name *key* to the the specified *value* to the first object that
    seems to support the property.
    """

    return self._resolve(key).set(value)

  def _resolve(self, key: str) -> _ValueRef:

    def _cant_be_set(_v):
      raise RuntimeError('cannot be set')

    if key == 'owner' and self.owner is not None:
      return _ValueRef(lambda: self.owner, _cant_be_set, 'closure owner')
    if key == 'delegate' and self.delegate is not None:
      return _ValueRef(lambda: self.delegate, _cant_be_set, 'closure delegate')

    if key in self.locals:
      return _ValueRef(lambda: self.locals[key], _cant_be_set, 'closure locals')

    if self.resolve_strategy == ResolveStrategy.OWNER_FIRST:
      objs = (self.owner, self.delegate)
    elif self.resolve_strategy == ResolveStrategy.DELEGATE_FIRST:
      objs = (self.delegate, self.owner)
    else:
      assert False, self.resolve_strategy

    for obj in filter(lambda x: x is not None, objs):
      if isinstance(obj, Closure):
        try:
          return obj._resolve(key)
        except NameError:
          continue
      if hasattr(obj, key) or key in getattr(type(obj), '__annotations__', {}):
        return _ValueRef.attr(obj, key)

    if self.stackframe:
      if key in self.stackframe.f_locals:
        return _ValueRef.frame_locals(self.stackframe, key)
      if key in self.stackframe.f_globals:
        return _ValueRef.frame_globals(self.stackframe, key)

    if key in vars(builtins):
      return _ValueRef.builtin(key)

    raise NameError(key, objs)


def closure(owner: t.Optional[t.Any] = None, frame: t.Optional[types.FrameType] = None,
  capture_frame: bool = True) -> t.Callable[[t.Callable], Closure]:
  """
  Decorator for closure functions.
  """

  if frame is None and capture_frame:
    frame = sys._getframe(1)

  def decorator(func: t.Callable) -> Closure:
    return Closure(func, frame, owner, None)

  return decorator


@t.runtime_checkable
class IConfigurable(t.Protocol):

  def __call__(self, closure: 'Closure') -> t.Any:
    """ Syntactic sugar for DSL code. """

    return self.configure(closure)

  def configure(self: T, closure: 'Closure') -> T:
    """ Configure the object with a closure. """

    closure.apply(self)
    return self

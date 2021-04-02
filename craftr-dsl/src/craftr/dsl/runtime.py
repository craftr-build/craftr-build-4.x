
import abc
import builtins
import contextlib
import functools
import sys
import threading
import typing as t
from itertools import chain

from .macros import MacroPlugin
from .transpiler import compile_file

T = t.TypeVar('T')
T_Callable = t.TypeVar('T_Callable', bound=t.Callable)


class NameProvider(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def _lookup_name(self, name: str) -> t.Any:
    pass


class PropertyOwner(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def _set_property_value(self, name: str, value: t.Any) -> None:
    pass


class Runtime:
  """
  A runtime object supports the execution of a Python module transpiled from the Craftr DSL. The
  runtime is a thread-safe object that keeps track of the closure targets and local variables in
  order to implement the name resolution.
  """

  def __init__(self, initial: t.Any):
    self._initial = initial
    self._threadlocal = threading.local()

  @property
  def _threadlocal_stack(self) -> t.List[t.Any]:
    try:
      return self._threadlocal.stack
    except AttributeError:
      stack = self._threadlocal.stack = []
      if self._initial is not None:
        stack.append(self._initial)
      return stack

  def closure(self) -> t.Callable[[T_Callable], T_Callable]:
    """
    Mark a function as being a closure. Effectively this just pushes the first argument of the
    closure on the threadlocal stack for name resolution.
    """

    def decorator(func):
      @functools.wraps(func)
      def wrapper(ctx, *args, **kwargs):
        with self.pushing(ctx):
          return func(ctx, *args, **kwargs)
      return wrapper

    return decorator

  def push(self, ctx: t.Any) -> None:
    self._threadlocal_stack.append(ctx)

  def pop(self) -> t.Any:
    return self._threadlocal_stack.pop()

  @contextlib.contextmanager
  def pushing(self, ctx: t.Any) -> t.Iterator[None]:
    try:
      self.push(ctx)
      yield
    finally:
      assert self.pop() is ctx

  def lookup(self, name: str) -> t.Any:
    """
    Performs a lookup for a variable. First, it checks the locals of the calling frame. Then, it
    checks the dictionaries or object's stored on the runtime's thread-local stack. Finally, the
    calling frame's globals are checked.
    """

    frame = sys._getframe(1)
    try:
      prefix = [frame.f_locals]
      # If the current frame is a class body, we take the parent frame into account (where the
      # class is declared in.
      if frame.f_code.co_name != '<module>' and frame.f_code.co_flags == 64:  # NOFREE
        prefix.append(frame.f_back.f_locals)
      for item in chain(prefix, reversed(self._threadlocal_stack), [frame.f_globals, builtins]):
        if isinstance(item, t.Mapping):
          if name in item:
            return item[name]
        else:
          try:
            return getattr(item, name)
          except AttributeError:
            pass
          if hasattr(item, '_lookup_name'):
            try:
              return item._lookup_name(name)
            except KeyError:
              pass
      raise NameError(name, self._threadlocal_stack)
    finally:
      del frame

  def configure_object(self, obj: T, closure: t.Callable[[T], None]) -> None:
    """
    This method is called for a closure to configure an object.
    """

    if hasattr(obj, 'configure'):  # NameProvider
      obj.configure(closure)
    elif isinstance(obj, dict):
      # TODO(NiklasRosenstein): Maybe we should instead use a wrapper for the same dict.
      class namespace:
        def __repr__(self) -> str:
          return f'namespace({self.__dict__})'
      temp = namespace
      for key, value in obj.items():
        temp.__dict__[key] = value
      closure(temp)
      obj.clear()
      obj.update(temp.__dict__)
      obj.pop('__doc__', None)
      obj.pop('__dict__', None)
      obj.pop('__module__', None)
      obj.pop('__repr__', None)
      obj.pop('__weakref__', None)
    else:
      closure(obj)

  def set_object_property(self, obj: T, name, value: t.Any) -> None:
    if hasattr(obj, '_set_property_value'):  # PropertyOwner
      try:
        obj._set_property_value(name, value)
        return
      except AttributeError:
        pass
    setattr(obj, name, value)

  __getitem__ = lookup


def run_file(
  context: t.Any,
  globals: t.Dict[str, t.Any],
  filename: str,
  fp: t.Optional[t.TextIO] = None,
  macros: t.Optional[t.Dict[str, MacroPlugin]] = None,
) -> None:

  globals['self'] = context
  globals['__runtime__'] = Runtime(context)

  module = compile_file(filename, fp, macros)
  code = compile(module, filename=filename, mode='exec')
  exec(code, globals)


__all__ = ['NameProvider', 'PropertyOwner', 'Runtime', 'run_file']

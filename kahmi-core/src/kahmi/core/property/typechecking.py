
"""
Runtime type checking for properties based on type hints.
"""

import abc
import contextlib
import typing as t
from typing import _type_repr as type_repr    # type: ignore

from kahmi.core.util.typing import unpack_type_hint

_type_checking_handlers: t.Dict[t.Any, 'TypeCheckingHandler'] = {}


class TypeCheckingError(Exception):
  pass


class Key:

  def __init__(self, val: t.Any) -> None:
    self.val = val

  def __repr__(self) -> str:
    return f'Key({self.val!r})'


class BaseContext:

  def __init__(self, type_hint: t.Any) -> None:
    self._path: t.List[t.Any] = []
    self._type_hints: t.List[t.Any] = [type_hint]

  @property
  def root_type_hint(self) -> t.Any:
    return self._type_hints[0]

  @property
  def type_hint(self) -> t.Any:
    return self._type_hints[-1]

  @property
  def path(self) -> str:
    if not self._path:
      return '$'
    return '$.' + '.'.join(repr(x) for x in self._path)

  @contextlib.contextmanager
  def push(self, value: t.Any, type_hint: t.Any) -> t.Iterator[None]:
    self._path.append(value)
    self._type_hints.append(type_hint)
    try:
      yield
    finally:
      self._path.pop()
      self._type_hints.pop()

  @contextlib.contextmanager
  def push_type_hint_only(self, type_hint: t.Any) -> t.Iterator[None]:
    self._type_hints.append(type_hint)
    try:
      yield
    finally:
      self._type_hints.pop()


class TypeCheckingContext(BaseContext):

  def __init__(self,
    type_hint: t.Any,
    message_prefix: t.Optional[t.Callable[[], str]] = None,
    force_accept: t.Optional[t.Callable[[t.Any], bool]] = None) -> None:
    super().__init__(type_hint)
    self._message_prefix = message_prefix
    self._force_accept_func = force_accept

  def force_accept_value(self, value: t.Any, type_hint_args: t.List[t.Any]) -> bool:
    if self._force_accept_func is not None:
      return self._force_accept_func(value)
    return False

  def type_error(self, current_value: t.Any, expected_type: t.Any) -> TypeCheckingError:
    """ Constructs a #TypeError with information from the context. """

    if self._message_prefix is not None:
      message = self._message_prefix()
    else:
      message = ''

    message += f'at {self.path}: found {type_repr(type(current_value))} but '
    message += f'expected {type_repr(expected_type)}'

    return TypeCheckingError(message)


class MutableVisitContext(BaseContext):

  def __init__(self,
    type_hint: t.List[t.Any],
    mutator_func: t.Optional[t.Callable[[t.Any], t.Any]] = None,
    always: bool = False,
  ) -> None:
    super().__init__(type_hint)
    self._mutator_func = mutator_func
    self.always = always

  def mutate(self, value: t.Any, type_hint_args: t.List[t.Any]) -> t.Any:
    if self._mutator_func:
      return self._mutator_func(value, type_hint_args, self)
    return value

  def to_type_checking(self, message_prefix: t.Optional[t.Callable[[], str]] = None) -> 'TypeCheckingContext':
    result = TypeCheckingContext(self.root_type_hint, message_prefix)
    result._path[:] = self._path
    result._type_hints[:] = self._type_hints
    return result


class TypeCheckingHandler(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def checked_visit(self, value: t.Any, type_hint_args: t.List[t.Any], context: TypeCheckingContext) -> None:
    pass

  @abc.abstractmethod
  def mutable_visit(self, value: t.Any, type_hint_args: t.List[t.Any], context: MutableVisitContext) -> None:
    pass


def register_type_handler(type_: t.Any, type_checking_handler: TypeCheckingHandler) -> None:
  _type_checking_handlers[type_] = type_checking_handler


class _SequenceHandler(TypeCheckingHandler):

  def _is_sequence(self, value: t.Any) -> bool:
    return isinstance(value, t.Sequence) and not isinstance(value, (str, bytes, bytearray, memoryview))

  def checked_visit(self, value: t.Any, type_hint_args: t.List[t.Any], context: TypeCheckingContext) -> None:
    assert self._is_sequence(value), type(value)
    assert not type_hint_args or len(type_hint_args) == 1, type_hint_args
    if type_hint_args:
      for index, item in enumerate(value):
        with context.push(index, type_hint_args[0]):
          check_type(item, context)

  def mutable_visit(self, value: t.Any, type_hint_args: t.List[t.Any], context: MutableVisitContext) -> t.Any:
    if not self._is_sequence(value):
      return value
    assert not type_hint_args or len(type_hint_args) == 1, type_hint_args
    sub_type_hint = type_hint_args[0] if type_hint_args else t.Any
    def generator(it):
      for index, item in enumerate(it):
        with context.push(index, sub_type_hint):
          yield mutate_values(item, context)
    return type(value)(generator(iter(value)))


class _MappingHandler(TypeCheckingHandler):

  def checked_visit(self, value: t.Any, type_hint_args: t.List[t.Any], context: TypeCheckingContext) -> None:
    assert isinstance(value, t.Mapping), type(value)
    assert not type_hint_args or len(type_hint_args) == 2, type_hint_args
    if type_hint_args:
      for key, value in value.items():
        with context.push(Key(key), type_hint_args[0]):
          check_type(key,  context)
        with context.push(key, type_hint_args[1]):
          check_type(value, context)

  def mutable_visit(self, value: t.Any, type_hint_args: t.List[t.Any], context: MutableVisitContext) -> t.Any:
    if not isinstance(value, t.Mapping):
      return value
    assert not type_hint_args or len(type_hint_args) == 2, type_hint_args
    value_type_hint = type_hint_args[1] if type_hint_args else t.Any
    def generator(it):
      for key, value in it:
        with context.push(key, value_type_hint):
          new_value = mutate_values(value, context)
        yield (key, new_value)
    return type(value)(generator(value.items()))  # type: ignore


class _UnionHandler(TypeCheckingHandler):

  def checked_visit(self, value: t.Any, type_hint_args: t.List[t.Any], context: TypeCheckingContext) -> None:
    original_errors: t.List[TypeCheckingError] = []
    for type_hint in type_hint_args:
      with context.push_type_hint_only(type_hint):
        try:
          check_type(value, context)
          return
        except TypeCheckingError as exc:
          original_errors.append(exc)
    # TODO(NiklasRosenstein): Do something useful with the original errors.
    #print(type_hint_args, repr(value))
    raise context.type_error(value, t.Union[tuple(type_hint_args)])

  def mutable_visit(self, value: t.Any, type_hint_args: t.List[t.Any], context: MutableVisitContext) -> t.Any:
    for type_hint in type_hint_args:
      with context.push_type_hint_only(type_hint):
        try:
          check_type_current(value, context.to_type_checking())
        except TypeCheckingError:
          continue
        return mutate_values(value, context)
    raise context.to_type_checking().type_error(value, t.Union[tuple(type_hint_args)])


register_type_handler(t.Sequence, _SequenceHandler())
register_type_handler(t.List, _SequenceHandler())
register_type_handler(list, _SequenceHandler())
register_type_handler(t.Mapping, _MappingHandler())
register_type_handler(t.MutableMapping, _MappingHandler())
register_type_handler(t.Dict, _MappingHandler())
register_type_handler(dict, _MappingHandler())
register_type_handler(t.Union, _UnionHandler())


def check_type_current(value: t.Any, context: TypeCheckingContext) -> None:
  type_, _type_args = unpack_type_hint(context.type_hint)

  if type_ is None:
    raise TypeError(f'invalid type_hint: {context.type_hint!r}')

  type_is_type = isinstance(type_, type)
  if type_is_type and not isinstance(value, type_):
    raise context.type_error(value, type_)


def check_type(
  value: t.Any,
  context: TypeCheckingContext,
) -> None:
  """
  Checks if the type of *value* matches the specified *type_hint*. The check is performed
  recursively to exhaustively verify the value type.
  """

  type_, type_args = unpack_type_hint(context.type_hint)
  type_is_type = isinstance(type_, type)

  if context.force_accept_value(value, type_args):
    return

  check_type_current(value, context)

  handler = _type_checking_handlers.get(type_)
  if not handler and not type_is_type:
    raise RuntimeError(f'no handler registered for {type_repr(type_)!r}')
  if handler is not None:
    handler.checked_visit(value, type_args, context)


def mutate_values(
  value: t.Any,
  context: MutableVisitContext,
) -> t.Any:

  type_, type_args = unpack_type_hint(context.type_hint)

  if context.always:
    value = context.mutate(value, type_args)

  if type_ is None:
    raise TypeError(f'invalid type_hint: {context.type_hint!r}')

  handler = _type_checking_handlers.get(type_)
  if not handler:
    return context.mutate(value, type_args)

  return handler.mutable_visit(value, type_args, context)

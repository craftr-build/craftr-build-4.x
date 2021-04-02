
import abc
import types
import typing as t

from kahmi.core.util.preconditions import check_instance_of

T = t.TypeVar('T')
U = t.TypeVar('U')
V = t.TypeVar('V')


def _add_operator(left: t.Any, right: t.Any) -> t.Any:
  """
  Implements the addition behaviour for properties.
  """

  if isinstance(left, t.Sequence) and right is None:
    return left
  elif isinstance(right, t.Sequence) and left is None:
    return right
  elif not isinstance(left, str) and isinstance(left, t.Sequence) and isinstance(right, t.Sequence):
    return list(left) + list(right)
  return left + right


class NoValueError(Exception):
  """ Raised when a provider has no value. """


class Provider(t.Generic[T], metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def get(self) -> T:
    """ Get the value of the propery, or raise a #NoValueError. """

  def or_else(self, default: U) -> t.Union[T, U]:
    """ Get the value of the property, or return *default*. """

    try:
      return self.get()
    except NoValueError:
      return default

  def or_none(self) -> t.Optional[T]:
    """ Get the value of the property, or return None. """

    return self.or_else(None)

  def visit(self, func: t.Callable[['Provider'], bool]) -> None:
    func(self)

  def __add__(self, other: t.Union[T, 'Provider[T]']) -> 'Provider[T]':
    return BinaryProvider(_add_operator, self, Provider.of(other))

  def __radd__(self, other: t.Union[T, 'Provider[T]']) -> 'Provider[T]':
    return BinaryProvider(_add_operator, Provider.of(other), self)

  def __iadd__(self, other: t.Union[T, 'Provider[T]']) -> 'Provider[T]':
    return BinaryProvider(_add_operator, self, Provider.of(other))

  @staticmethod
  def of(value: t.Union[T, 'Provider[T]']) -> 'Provider[T]':
    if not isinstance(value, Provider):
      return Box(value)
    return value


class Box(Provider[T]):

  def __init__(self, value: t.Optional[T]) -> None:
    self._value = value

  def get(self) -> T:
    if self._value is None:
      raise NoValueError
    return self._value


def _visit_captured_providers(subject: t.Callable, func: t.Callable[[Provider], bool]) -> None:
  assert isinstance(subject, types.FunctionType), type(subject)
  for cell in (subject.__closure__ or []):
    if isinstance(cell.cell_contents, Provider):
      cell.cell_contents.visit(func)


class UnaryProvider(Provider[T]):

  def __init__(self, func: t.Callable[[t.Optional[U]], t.Optional[T]], inner: Provider[U]) -> None:
    check_instance_of(inner, Provider)
    self._func = func
    self._inner = inner

  def get(self) -> T:
    value = self._func(self._inner.or_none())
    if value is None:
      raise NoValueError
    return value

  def visit(self, func: t.Callable[[Provider], bool]) -> None:
    if func(self):
      self._inner.visit(func)
      _visit_captured_providers(self._func, func)


class BinaryProvider(Provider[T]):

  def __init__(self,
    func: t.Callable[[t.Optional[U], t.Optional[V]], T],
    left: Provider[U],
    right: Provider[V],
  ) -> None:
    check_instance_of(left, Provider)
    check_instance_of(right, Provider)
    self._func = func
    self._left = left
    self._right = right

  def get(self) -> T:
    value = self._func(self._left.or_none(), self._right.or_none())
    if value is None:
      raise NoValueError
    return value

  def visit(self, func: t.Callable[[Provider], bool]) -> None:
    if func(self):
      self._left.visit(func)
      self._right.visit(func)
      _visit_captured_providers(self._func, func)

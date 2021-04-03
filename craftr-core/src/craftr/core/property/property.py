
import typing as t
import weakref

from craftr.core.util.preconditions import check_not_none
from craftr.core.util.typing import unpack_type_hint
from .provider import Box, NoValueError, Provider, T
from .typechecking import TypeCheckingContext, type_repr, check_type, mutate_values, MutableVisitContext


def _unpack_nested_providers(value: t.Any, type_hint: t.Any) -> t.Any:
  def mutator(value: t.Any, type_hint_args: t.List[t.Any], context: MutableVisitContext) -> t.Any:
    if isinstance(value, Provider):
      return value.get()
    return value
  return mutate_values(value, MutableVisitContext(type_hint, mutator, True))


class Property(Provider[T]):
  """
  Properties are mutable providers that sit as attributes on objects of the #HavingProperties
  base class. The type hint of a property is passed into it's construct when the annotation is
  defined on the #HavingProperties class level.

  Properties perform extensive runtime type checking when setting a bare value and after
  evaluating it.
  """

  def __init__(self,
    value_type: t.Any,
    annotations: t.List[t.Any],
    name: str,
    origin: t.Optional['HavingProperties']
  ) -> None:
    self.value_type = value_type
    self.annotations = annotations
    self.name = name
    self._origin = weakref.ref(origin) if origin is not None else None
    self._value: t.Optional[Provider[T]] = None
    self._nested_providers: t.List[Provider] = []

  def __repr__(self) -> str:
    return f'{type(self).__name__}[{type_repr(self.value_type)}]({self.fqn!r})'

  @property
  def fqn(self) -> str:
    if self._origin is None:
      return self.name
    return type(self.origin).__name__ + '.' + self.name

  @property
  def origin(self) -> t.Optional['HavingProperties']:
    return check_not_none(self._origin(), 'lost reference to origin') \
        if self._origin is not None else None

  def set(self, value: t.Union[T, Provider[T]]) -> None:
    nested_providers: t.List[Provider] = []
    if not isinstance(value, Provider):
      # TODO(NiklasRosenstein): `force_accept` parameter should check if the types match.
      def force_accept(value: t.Any) -> bool:
        if isinstance(value, Provider):
          nested_providers.append(value)
          return True
        return False
      check_type(
        value,
        TypeCheckingContext(
          type_hint=self.value_type,
          message_prefix=lambda: f'while setting property {self.fqn}: ',
          force_accept=force_accept))
      value = Box(value)
    self._value = value
    self._nested_providers = nested_providers

  def get(self) -> T:
    if self._value is None:
      raise NoValueError(self.fqn)
    value = _unpack_nested_providers(self._value.get(), self.value_type)
    check_type(value, TypeCheckingContext(self.value_type, lambda: f'while getting property {self.fqn}: '))
    return value

  def visit(self, func: t.Callable[[Provider], bool]) -> None:
    if func(self) and self._value is not None:
      self._value.visit(func)
      for provider in self._nested_providers:
        provider.visit(func)


class HavingProperties:
  """
  Base for classes that have properties declared as annotations at the class level. Setting
  property values will automatically wrap them in a #Provider if the value is not already one.
  The constructor will take care of initializing the properties.
  """

  def __init__(self, **kwargs: t.Any) -> None:
    self.__properties: t.Dict[str, Property] = {}

    for key, value in t.get_type_hints(type(self), include_extras=True).items():

      type_, args = unpack_type_hint(value)
      if type_ is None:
        continue

      annotations: t.List[t.Any] = []
      if type_ == t.Annotated:  # type: ignore
        type_, annotations = args[0], list(args[1:])
        type_, args = unpack_type_hint(type_)

      if not isinstance(type_, type) or not issubclass(type_, Property):
        continue

      if len(args) == 0:
        value_type = t.Any
      elif len(args) == 1:
        value_type = args[0]
      else:
        raise RuntimeError('Too many arguments for Property[...] generic', type(self).__name__, key)

      # Also accept annotations in the value argument of the Property[] generic.
      if unpack_type_hint(value_type)[0] == t.Annotated:   # type: ignore
        _, args = unpack_type_hint(value_type)
        value_type = args[0]
        # NOTE(NiklasRosenstein): Visually, the annotations of the inner t.Annotated hint will
        #   appear before the annotations of the outter hint, so we'll keep that order in tact.
        annotations = args[1:] + annotations

      prop = type_(value_type, annotations, key, self)
      setattr(self, key, prop)
      self.__properties[key] = prop

      if key in kwargs:
        setattr(self, key, kwargs[key])
        kwargs.pop(key)

    for key in kwargs:
      raise TypeError(f'{type(self).__name__}.{key} is not a property')

  def __setattr__(self, key: str, value: t.Any) -> None:
    try:
      prop = self.__properties.get(key)
    except AttributeError:
      pass
    else:
      if prop is not None:
        prop.set(value)
        return

    object.__setattr__(self, key, value)

  def get_properties(self) -> t.Dict[str, Property]:
    return self.__properties


def collect_properties(provider: t.Union[HavingProperties, Provider]) -> t.List[Property]:
  """
  Collects all #Property objects that are encountered when visiting the specified provider or
  all properties of a #HavingProperties instance.
  """

  result: t.List[Property] = []

  def _append_if_property(provider: Provider) -> bool:
    if isinstance(provider, Property):
      result.append(provider)
    return True

  if isinstance(provider, HavingProperties):
    for prop in provider.get_properties().values():
      prop.visit(_append_if_property)
  elif isinstance(provider, Provider):
    provider.visit(_append_if_property)
  else:
    raise TypeError('expected Provider or HavingProperties instance, '
      f'got {type(provider).__name__}')

  return result

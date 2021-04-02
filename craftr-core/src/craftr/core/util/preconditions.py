
import typing as t

T = t.TypeVar('T')


def check_argument(value: bool, message: t.Union[str, t.Callable[[], str]]) -> None:
  if not value:
    raise RuntimeError(message() if callable(message) else message)


def check_not_none(value: t.Optional[T], message: str) -> T:
  if value is None:
    raise RuntimeError(message)
  return value


def check_instance_of(
  value: t.Any,
  types: t.Union[t.Type, t.Tuple[t.Type, ...]],
  display_name: t.Union[None, str, t.Callable[[], str]] = None,
) -> None:

  if not isinstance(value, types):
    if isinstance(types, tuple):
      type_str = ', '.join(x.__name__ for x in types)
    else:
      type_str = types.__name__
    message = f'expected instance of {type_str}, got {type(value).__name__}'
    if display_name is not None:
      name = display_name() if callable(display_name) else display_name
      message = f'{name}: {message}'
    raise TypeError(message)

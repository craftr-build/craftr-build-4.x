
import abc
import typing as t

T = t.TypeVar('T')


class Config(metaclass=abc.ABCMeta):
  """
  Interface similar to a mapping but it provides additional helpers to read values of various
  types.
  """

  @abc.abstractmethod
  def __getitem__(self, key: str) -> str:
    pass

  @abc.abstractmethod
  def set(self, key: str, value: t.Union[str, int, bool]) -> None:
    pass

  def get(self, key: str, default: T) -> t.Union[str, T]:
    try:
      return self[key]
    except KeyError:
      return default

  def get_int(self, key: str, default: T) -> t.Union[int, T]:
    try:
      return int(self[key].strip())
    except KeyError:
      return default
    except ValueError:
      raise ValueError(f'{key!r} is not an integer: {self[key]!r}')

  def get_bool(self, key: str, default: T = False) -> t.Union[bool, T]:
    try:
      value = self[key].strip().lower()
    except KeyError:
      return default
    if value in ('yes', 'true', 'on', '1'):
      return True
    if value in ('no', 'false', 'off', '0'):
      return False
    raise ValueError(f'{key!r} is not a boolean: {self[key]!r}')

  @staticmethod
  def of(mapping: t.MutableMapping[str, str]) -> 'Config':
    return _MappingConfig(mapping)

  @staticmethod
  def parse(
    lines: t.Iterable[str],
    on_invalid_line: t.Optional[t.Callable[[int, str], None]] = None,
  ) -> 'Config':
    """
    Parses a list of `key=value` lines and returns it as a #Config object. Lines starting with
    the hashsign (`#`) are skipped. If provided, lines that do not conform to the `key=value`
    format are passed to `on_invalid_line` and are skipped.
    """

    mapping: t.Dict[str, str] = {}
    for index, line in enumerate(lines):
      line = line.strip()
      if line.startswith('#'):
        continue
      key, sep, value = line.partition('=')
      if not sep:
        if on_invalid_line:
          on_invalid_line(index, line)
        continue
      mapping[key.strip()] = value.strip()
    return _MappingConfig(mapping)


class _MappingConfig(Config):

  def __init__(self, mapping: t.MutableMapping[str, str]) -> None:
    self._mapping = mapping

  def __getitem__(self, key: str) -> str:
    return self._mapping[key]

  def set(self, key: str, value: t.Union[str, int, bool]) -> None:
    if not isinstance(value, (str, int, bool)):
      raise TypeError(f'expected typing.Union[str, int, bool], got {type(value).__name__}')
    self._mapping[key] = value

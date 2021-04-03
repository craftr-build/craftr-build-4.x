
"""
Describes the interface for extensible objects.
"""

import abc
import typing as t

T_IConfigurable = t.TypeVar('T_IConfigurable', bound='IConfigurable')

if t.TYPE_CHECKING:
  from craftr.core.closure import Closure


@t.runtime_checkable
class IConfigurable(t.Protocol):

  def configure(self, closure: 'Closure') -> t.Any:
    """
    Configure the object with a closure.
    """

    closure.apply(self)


class ExtensibleObject:

  def __init__(self) -> None:
    self._extensions: t.Dict[str, t.Any] = {}

  def __getattr__(self, key: t.Any) -> t.Any:
    try:
      return object.__getattribute__(self, '_extensions')[key]
    except KeyError:
      raise AttributeError(f'{self} has no attribute or extension named "{key}".')

  def add_extension(self, key: str, extension: t.Any) -> None:
    self._extensions[key] = extension

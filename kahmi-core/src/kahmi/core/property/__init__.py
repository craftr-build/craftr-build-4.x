
import typing as t

if not hasattr(t, 'Annotated'):
  raise EnvironmentError('requires Python 3.9+')

from .provider import NoValueError, Provider
from .property import Property, HavingProperties, collect_properties

__all__ = [
  'NoValueError',
  'Provider',
  'Property',
  'HavingProperties',
  'collect_properties',
]

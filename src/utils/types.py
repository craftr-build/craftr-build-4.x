"""
Useful datatypes and base classes.
"""

__all__ = ['NamedObject']

import sys

# This module requires Python 3.6 or newer (type annotations on class
# variables. ordered dictionaries, object.__init_subclass__()).
if sys.version < '3.6':
  raise EnvironmentError('Python 3.6+ required')


class NamedObject:
  """
  A base-class similar to #typing.NamedTuple, but mutable and with a proper
  #asdict() method (no `_asdict()`).

  Note that this class is also preferred as there is a bug in Python 3.6.0
  which prevents you from accessing additional members declared on the
  NamedTuple subclass (eg. functions and properties).
  """

  def __init_subclass__(cls, **kwargs):
    # Inherit the annotations of the base classes, in the correct order.
    annotations = getattr(cls, '__annotations__', {})
    new_annotations = {}
    for base in cls.__bases__:
      for key, value in getattr(base, '__annotations__', {}).items():
        if key not in annotations:
          new_annotations[key] = value
    new_annotations.update(annotations)
    cls.__annotations__ = new_annotations
    return super().__init_subclass__(**kwargs)

  def __init__(self, *args, **kwargs):
    annotations = getattr(self, '__annotations__', {})
    if len(args) > len(annotations):
      raise TypeError('{}() expected {} positional arguments, got {}'
        .format(type(self).__name__, len(annotations), len(args)))

    for arg, (key, ant) in zip(args, annotations.items()):
      setattr(self, key, arg)
      if key in kwargs:
        raise TypeError('{}() duplicate value for argument "{}"'
          .format(type(self).__name__, key))

    for key, ant in annotations.items():
      if key in kwargs:
        setattr(self, key, kwargs.pop(key))
      elif not hasattr(self, key):
        raise TypeError('{}() missing argument "{}"'
          .format(type(self).__name__, key))

    for key in kwargs.keys():
      raise TypeError('{}() unexpected keyword argument "{}"'
        .format(type(self).__name__, key))

  def __repr__(self):
    members = ', '.join('{}={!r}'.format(k, getattr(self, k)) for k in self.__annotations__)
    return '{}({})'.format(type(self).__name__, members)

  def __iter__(self):
    for key in self.__annotations__:
      yield getattr(self, key)

  def asdict(self):
    return {k: getattr(self, k) for k in self.__annotations__}

"""
Useful datatypes and base classes.
"""

__all__ = ['NamedObject']

import collections
import sys

# This module requires Python 3.6 or newer (type annotations on class
# variables. ordered dictionaries, object.__init_subclass__()).
if sys.version < '3.6':
  raise EnvironmentError('Python 3.6+ required')


class NamedObjectMeta(type):

  def __init__(self, name, bases, data):
    # Inherit the annotations of the base classes, in the correct order.
    annotations = getattr(self, '__annotations__', {})
    if isinstance(annotations, (list, tuple)):
      for i, item in enumerate(annotations):
        if len(item) == 3:
          setattr(self, item[0], item[2])
          item = item[:2]
          annotations[i] = item
      annotations = collections.OrderedDict(annotations)
    new_annotations = collections.OrderedDict()
    for base in bases:
      base_annotations = getattr(base, '__annotations__', {})
      if isinstance(base_annotations, (list, tuple)):
        base_annotations = collections.OrderedDict(base_annotations)
      for key, value in base_annotations.items():
        if key not in annotations:
          new_annotations[key] = value
    new_annotations.update(annotations)
    self.__annotations__ = new_annotations
    super().__init__(name, bases, data)


class NamedObject(metaclass=NamedObjectMeta):
  """
  A base-class similar to #typing.NamedTuple, but mutable. Fields can be
  specified using Python3.6 class-member annotations or by setting the
  `__annotations__` fields (as a list, as < 3.6 does not preserve order
  in dictionaries).

  Note that this class is also preferred as there is a bug in Python 3.6.0
  which prevents you from accessing additional members declared on the
  NamedTuple subclass (eg. functions and properties).
  """

  def __init__(self, *args, **kwargs):
    annotations = getattr(self, '__annotations__', {})
    if len(args) > len(annotations):
      raise TypeError('{}() expected {} positional arguments, got {}'
        .format(type(self).__name__, len(annotations), len(args)))
    if isinstance(annotations, (list, tuple)):
      annotations = collections.OrderedDict(annoations)

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

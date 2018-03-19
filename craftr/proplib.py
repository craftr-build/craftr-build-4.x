# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
"""
This module implements the #PropertySet class which is used to describe
properties and their datatype.
"""

import builtins
import nr.generic


class Prop:

  def __init__(self, name, type, default=NotImplemented, optional=True,
               readonly=False):
    if isinstance(type, builtins.type):
      if not issubclass(type, PropType):
        raise TypeError('expected PropType subclass', type)
      type = type()
    elif not isinstance(type, PropType):
      raise TypeError('expected PropType instance', builtins.type(type))
    if default is NotImplemented:
      if not optional:
        raise ValueError('property is not optional, need default value')
      if readonly:
        raise ValueError('property is readonly, need default value')
    self.name = name
    self.type = type
    self.default = default
    self.optional = optional
    self.readonly = readonly

  def __repr__(self):
    return 'Prop(name={!r}, type={!r}, default={!r}, optional={!r}, readonly={!r})'.format(
      self.name, self.type, self.default, self.optional, self.readonly)

  def get_default(self):
    if self.default is NotImplemented:
      return self.type.default()
    default = self.default
    if callable(default):
      default = default()
    return self.coerce(default)

  def coerce(self, value):
    if not self.optional or value is not None:
      value = self.type.coerce(self.name, value)
    return value


class PropType:
  """
  Base class for property datatype descriptors.
  """

  def coerce(self, name, value):
    """
    Called whenever a value is assigned to a property. This method is
    supposed to check the type of *value* and eventually coerce it to the
    proper Python datatype.
    """
    raise NotImplementedError

  def default(self):
    raise NotImplementedError

  def inherit(self, values):
    return next(values)

  @staticmethod
  def typeerror(name, expected, value):
    return TypeError('{}: expected {}, got {}'.format(
      name, expected, type(value).__name__))


class Bool(PropType):

  def __init__(self, strict=True):
    self.strict = strict

  def coerce(self, name, value):
    if self.strict and type(value) != bool:
      raise self.typeerror(name, 'bool', value)
    return bool(value)

  def default(self):
    return False


class Integer(PropType):

  def __init__(self, strict=False):
    self.strict = strict

  def coerce(self, name, value):
    if self.strict and type(value) != int:
      raise self.typeerror(name, 'int', value)
    try:
      return int(value)
    except (ValueError, TypeError):
      raise self.typeerror(name, 'int', value)

  def default(self):
    return 0


class String(PropType):

  def coerce(self, name, value):
    if not isinstance(value, str):
      raise self.typeerror(name, 'string', value)
    return value

  def default(self):
    return ''


class List(PropType, metaclass=nr.generic.GenericMeta):

  __generic_args__ = ['item_type']

  def __init__(self, item_type=None):
    if self.__generic_bind__:
      if item_type is not None:
        raise RuntimeError('can not override item_type after generic bind')
      item_type = self.item_type
    if isinstance(item_type, builtins.type):
      item_type = item_type()
    self.item_type = item_type

  def coerce(self, name, value):
    if isinstance(value, tuple):
      value = list(value)
    elif not isinstance(value, list):
      raise self.typeerror(name, 'list', value)
    if self.item_type:
      value = [self.item_type.coerce(name + '[' + str(i) + ']', x)
               for i, x in enumerate(value)]
    return value

  def default(self):
    return []

  def inherit(self, values):
    return [x for y in values for x in y]


class Dict(PropType, metaclass=nr.generic.GenericMeta):

  __generic_args__ = ['key_type', 'value_type']

  def __init__(self, key_type=None, value_type=None):
    if self.__generic_bind__:
      if key_type is not None:
        raise RuntimeError('can not override key_type after generic bind')
      if value_type is not None:
        raise RuntimeError('can not override value_type after generic bind')
      key_type = self.key_type
      value_type = self.value_type
    if isinstance(key_type, builtins.type):
      key_type = key_type()
    if isinstance(value_type, builtins.type):
      value_type = value_type()
    self.key_type = key_type
    self.value_type = value_type

  def coerce(self, name, value):
    if not isinstance(value, dict):
      raise self.typeerror(name, 'dict', value)
    if self.key_type:
      value = {self.key_type.coerce(name + '.key(' + repr(k) + ')', k): v
               for k, v in value.items()}
    if self.value_type:
      value = {k: self.value_type.coerce(name + '[' + repr(k) + ']', v)
               for k, v in value.items()}
    return value

  def default(self):
    return {}


StringList = List[String]


class PropertySet:
  """
  The #PropertySet describes a set of properties. It does not contain actual
  property values.
  """

  def __init__(self):
    self.props = {}

  def __repr__(self):
    return '<PropertySet props={}>'.format(self.props)

  def __getitem__(self, key):
    try:
      return self.props[key]
    except KeyError:
      raise NoSuchProperty(key)

  def __contains__(self, key):
    return key in self.props

  def __iter__(self):
    return iter(self.props.keys())

  def __len__(self):
    return len(self.propset)

  def add(self, prop_name, *args, **kwargs):
    if prop_name in self.props:
      raise ValueError('property name already used: {!r}'.format(prop_name))
    prop = Prop(prop_name, *args, **kwargs)
    self.props[prop_name] = prop
    return prop

  def items(self):
    return self.props.items()

  def keys(self):
    return self.props.keys()

  def values(self):
    return self.props.values()

  def get(self, key):
    return self.props.get(key)


class Properties:
  """
  A container for property values as declared in a #PropertySet.
  """

  def __init__(self, propset):
    self.propset = propset
    self.values = {}

  def __repr__(self):
    return 'Properties({})'.format(self.values)

  def __getitem__(self, key):
    prop = self.propset[key]
    try:
      return self.values[key]
    except KeyError:
      return prop.get_default()

  def __setitem__(self, key, value):
    prop = self.propset[key]
    if prop.readonly:
      raise ReadOnlyProperty(key)
    self.values[key] = prop.coerce(value)

  def __contains__(self, key):
    return key in self.propset

  def __iter__(self):
    return iter(self.propset)

  def __len__(self):
    return len(self.propset)

  def items(self):
    for key, prop in self.propset.items():
      try:
        yield (key, self.values[key])
      except KeyError:
        yield (key, prop.get_default())

  def keys(self):
    return iter(self.propset)

  def values(self):
    for key, prop in self.propset.items():
      try:
        yield self.values[key]
      except KeyError:
        yield prop.get_default()

  def has_value(self, key):
    """
    Similar to #is_set(), but this method will also return #True if a default
    value was explicitly set in the property.
    """

    prop = self.propset.get(key)
    if prop is None:
      return False
    if prop.default is not NotImplemented:
      return True
    return key in self.values

  def is_set(self, key):
    """
    Returns #True if the property identified by the specified *key* has a
    value set. Note that even if a property has no value set, the property's
    type's default value will be returned when accessing it.
    """

    return key in self.values


class NoSuchProperty(KeyError):
  pass


class ReadOnlyProperty(ValueError):
  pass

"""
This module provides classes to describe a collection of typed properties,
and applying these properties to containers for these properties. Property
values types are validated immediately.
"""

import collections


class Prop:

  def __init__(self, name, type, default=NotImplemented, optional=True, readonly=False):
    if default is NotImplemented:
      if not optional:
        raise ValueError('property is not optional, need default value')
    self.name = name
    self.type = type
    self.default = default
    self.optional = optional
    self.readonly = readonly

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


class List(PropType):

  def __init__(self, item_type=None):
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


class Dict(PropType):

  def __init__(self, key_type=None, value_type=None):
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


class PropertySet:
  """
  A property set is a collection of property declarations that can be used
  in a #Properties object.
  """

  class Scope:

    def __init__(self, name):
      if '.' in name:
        raise ValueError('invalid scope name: {!r}'.format(name))
      self.name = name
      self.props = {}

    def __repr__(self):
      return '<PropertySet.Scope name={!r} len(props)={}>'.format(
        self.name, len(self.props))

    def __getitem__(self, key):
      return self.props[key]

    def __contains__(self, key):
      return key in self.props

    def __iter__(self):
      return self.props.keys()

    def add(self, prop_name, *args, **kwargs):
      full_name = self.name + '.' + prop_name
      if '.' in prop_name:
        raise ValueError('invalid property name: {!r}'.format(full_name))
      if prop_name in self.props:
        raise ValueError('property name already used: {!r}'.format(full_name))
      prop = Prop(full_name, *args, **kwargs)
      self.props[prop_name] = prop
      return prop

  def __init__(self):
    self.scopes = {}

  def __getitem__(self, key):
    return self.scopes[key]

  def __contains__(self, key):
    return key in self.scopes

  def __repr__(self):
    return '<PropertySet len(scopes)={}>'.format(len(self.scopes))

  def __iter__(self):
    return self.scopes.keys()

  def add(self, scope_name):
    if scope_name in self.scopes:
      raise ValueError('scope already exists: {!r}'.format(scope_name))
    scope = self.Scope(scope_name)
    self.scopes[scope_name] = scope
    return scope


class Properties:
  """
  A container for property values as declared in a #PropertySet.
  """

  class Scope:

    def __init__(self, scopedef):
      assert isinstance(scopedef, PropertySet.Scope), type(scopedef)
      self.scopedef = scopedef
      self.values = {}

    def __repr__(self):
      return '<Properties.Scope name={!r}>'.format(self.scopedef.name)

    def __getitem__(self, key):
      try:
        return self.values[key]
      except KeyError:
        if key in self.scopedef:
          prop = self.scopedef[key]
          value = self.values[key] = prop.get_default()
          return value

    def __setitem__(self, key, value):
      prop = self.scopedef[key]
      self.values[key] = prop.coerce(value)

    def __contains__(self, key):
      return key in self.scopedef

    def __iter__(self):
      return iter(self.property_scope)

    @property
    def name(self):
      return self.scopedef.name

  def __init__(self, propset):
    self.propset = propset
    self.scopes = {}

  def __getitem__(self, key):
    if '.' in key:
      scope_name, prop_name = key.split('.', 1)
      scope = self.scope(scope_name)
      try:
        return scope[prop_name]
      except KeyError:
        raise KeyError(key)
    else:
      raise KeyError(key)

  def __setitem__(self, key, value):
    if '.' in key:
      scope_name, prop_name = key.split('.', 1)
      scope = self.scope(scope_name)
      scope[prop_name] = value
    else:
      raise KeyError(key)

  def __contains__(self, key):
    return key in self.scopes

  def __iter__(self):
    return self.scopes.keys()

  def scope(self, name):
    try:
      result = self.scopes[name]
    except KeyError:
      if name not in self.propset:
        raise
      result = self.scopes[name] = self.Scope(self.propset[name])
    return result

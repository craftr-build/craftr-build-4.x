
class Property:

  def __init__(self, name, type, default=None, readonly=False):
    if not hasattr(self, '_typecheck_' + type):
      raise ValueError('invalid property type: {}'.format(type))
    self.scope, self.name = name.split('.')
    self.type = type
    self.default = default
    self.readonly = readonly

    if type == 'StringList' and default is None:
      self.default = ()

  def __repr__(self):
    return 'Property(name={!r}, type={!r}, readonly={!r})'.format(
      self.name, self.type, self.readonly)

  def typecheck(self, value):
    if value is None:
      return None
    checker = getattr(self, '_typecheck_' + self.type)
    try:
      return checker(value)
    except ValueError as exc:
      raise ValueError('{}.{}: {}'.format(self.scope, self.name, exc))

  def inherit(self, value, other_values):
    method = getattr(self, '_inherit_' + self.type, None)
    if method is None:
      if value is not None:
        return value
      for value in other_values:
        if value is not None:
          return value
      return None
    return method(value, other_values)

  @staticmethod
  def _typecheck_String(value):
    if not isinstance(value, str):
      raise ValueError('expected String, got {} instead'.format(type(value).__name__))
    return value

  @staticmethod
  def _typecheck_StringList(value):
    if isinstance(value, tuple):
      value = list(value)
    if not isinstance(value, list):
      raise ValueError('expected StringList, got {} instead'.format(type(value).__name__))
    for item in value:
      if not isinstance(item, str):
        raise ValueError('expected String in StringList, found {}'.format(type(item).__name__))
    return value

  @staticmethod
  def _typecheck_Bool(value):
    if not isinstance(value, bool):
      raise ValueError('expected Bool, got {}'.format(type(value).__name__))
    return value

  @staticmethod
  def _typecheck_Int(value):
    if type(value) is not int:  # bool is a subclass
      raise ValueError('expected Int, got {}'.format(type(value).__name__))
    return value

  @staticmethod
  def _inherit_StringList(value, other_values):
    if value is None:
      result = []
    else:
      result = list(value)
    for value in other_values:
      if value is not None:
        result += value
    return result


class PropertySet:

  class _Namespace:
    def __init__(self, scope_name):
      self._scope_name = scope_name
    def __repr__(self):
      return 'namespace({})'.format(self._scope_name)

  def __init__(self, supports_exported_members=False):
    self._properties = {}
    self._namespaces = {}
    self._supports_exported_members = supports_exported_members

  def __getitem__(self, key):
    return self.namespace(key)

  def define_property(self, name, type, default=None, readonly=False):
    prop = Property(name, type)
    self._properties.setdefault(prop.scope, {})[prop.name] = prop
    if prop.scope not in self._namespaces:
      ns = self._Namespace(prop.scope)
      if self._supports_exported_members:
        ns.__exported__ = self._Namespace(prop.scope + '[export]')
      self._namespaces[prop.scope] = ns
    else:
      ns = self._namespaces[prop.scope]
    setattr(ns, prop.name, default)
    if self._supports_exported_members:
      setattr(ns.__exported__, prop.name, None)

  def properties(self, scope=None):
    if scope is not None:
      yield from self._properties[scope].values()
    else:
      for props in self._properties.values():
        yield from props.values()

  def scopes(self):
    return self._properties.keys()

  def namespace(self, scope):
    return self._namespaces[scope]

  def namespaces(self):
    for scope in self.scopes():
      yield scope, self._namespaces[scope]

  def get_property(self, property, default=None, inherit=True):
    scope, name = property.split('.')
    if scope not in self._properties:
      raise KeyError('scope does not exist: {}'.format(scope))
    props = self._properties[scope]
    if name not in props:
      raise KeyError('property does not exist: {}'.format(property))
    prop = props[name]
    namespace = self._namespaces[scope]
    try:
      value = prop.typecheck(getattr(namespace, name))
    except ValueError as exc:
      raise InvalidPropertyValue(self, str(exc))
    def iter_inheritance():
      if self._supports_exported_members:
        try:
          yield prop.typecheck(getattr(namespace.__exported__, name))
        except ValueError as exc:
          raise InvalidPropertyValue(self, '[export] ' + str(exc))
      for propset in self._inherited_propsets():
        try:
          yield propset.get_property(property, inherit=False)
        except KeyError:
          pass
    if inherit:
      value = prop.inherit(value, iter_inheritance())
    if value is None:
      value = default
    return value

  def _inherited_propsets(self):
    return; yield


class InvalidPropertyValue(ValueError):

  def __init__(self, propset, message):
    self.propset = propset
    self.message = message

  def __str__(self):
    return '{}: {}'.format(self.propset, self.message)

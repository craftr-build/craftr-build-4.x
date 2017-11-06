"""
Reader/writer for TOML configuration files with filter support. Properties
that can be filtered must be explicitly specified on the #Configuration object
before reading.

# Example

```toml
[native]
toolkit = "llvm"

[native.'cfg(win32)']
toolkit = "msvc"
```
"""

import fnmatch
import toml
import typing as t


def match(filter_type, filter_value, value):
  """
  Helper function that the #Configuration uses to match filters with property
  values.
  """

  if filter_type in ('=', '=='):
    return filter_value == value
  elif filter_type == '!=':
    return filter_value != value
  elif filter_type == '%':
    return filter_value in value
  elif filter_type == '~':
    return fnmatch.fnmatch(value, filter_value)
  else:
    raise ValueError('unsupported filter type: {!r}'.format(filter_type))


class OptionKey:

  def __init__(self, scope, name):
    self.scope = scope
    self.name = name

  def __repr__(self):
    return 'OptionKey(scope={!r}, name={!r})'.format(self.scope, self.name)

  def __iter__(self):
    yield self.scope
    yield self.name

  @classmethod
  def parse(cls, s: str, allow_empty_name: bool = False) -> 'OptionKey':
    scope, sep, name = s.rpartition('.')
    if not scope and not sep:
      scope, name = name, ''
    valid = scope and ((sep and name) or allow_empty_name)
    if not valid:
      raise ValueError('invalid option key: {!r}'.format(s))
    return cls(scope, name)


class Configuration:
  """
  Parses TOML files and evaluates filters in section headers. The properties
  that can be used for filtering can be specified in the #props member.

  Example syntax:

      ["gcc; clang; platform=windows; arch=amd64"]
        options...

  Available filters:

    * =, ==
    * !=
    * ~
    * %
  """

  def __init__(self, props=None):
    self._read_data = {}
    self._data = {}
    self.props = {} if props is None else props

  def filter_section(self, section):
    """
    Parse the specified section name and return a list of section names that
    this section represents. If the filters in this section do not apply to
    the #props in this Configuration, #None is returned.
    """

    names = []
    filters = ['=', '==', '!=', '~', '%']
    for part in (x.strip() for x in section.split(';')):
      f = next((f for f in filters if f in part), None)
      if f:
        prop, value = part.partition(f)[::2]
        have_value = self.props.get(prop, '')
        try:
          matches = match(f, value, have_value)
        except ValueError:
          matches = False
        if not matches:
          return None
      elif part:
        names.append(part)
    return names

  def read(self, filename: str) -> None:
    with open(filename, 'r') as fp:
      # TODO: Catch possible ValueError (and others?) and transform them
      #       into a proper exception for configuration parsing.
      data = toml.load(fp)

    for key in list(data.keys()):
      scopes = self.filter_section(key)
      if not scopes: continue
      options = data[key]
      for scope in scopes:
        if scope not in self._data:
          self._data[scope] = {}
        self._data[scope].update(options)

  def write(self, filename: str) -> None:
    with open(filename, 'w') as fp:
      self._parser.write(fp)

  def __getitem__(self, key: str) -> t.Any:
    try:
      scope, name = OptionKey.parse(key)
    except ValueError:
      raise KeyError(key)
    if scope not in self._data:
      raise KeyError(key)
    if name not in self._data[scope]:
      raise KeyError(key)
    return self._data[scope][name]

  def __setitem__(self, key: str, value: t.Any):
    try:
      scope, name = OptionKey.parse(key)
    except ValueError:
      raise KeyError(key)
    if scope not in self._data:
      self._data[scope] = {}
    self._data[scope][name] = value

  def __delitem__(self, key: str):
    try:
      scope, name = OptionKey.parse(key, allow_empty_name=True)
    except ValueError:
      raise KeyError(key)
    if not name:
      del self._data[scope]
    else:
      del self._data[scope][name]

  def get(self, key: str, default: t.Any = None) -> t.Any:
    try:
      return self[key]
    except KeyError:
      return default

  def sections(self) -> t.List[str]:
    return self._data.keys()

  def options(self, section: str = None) -> t.List[str]:
    if not section:
      options = []
      for section in self._data.keys():
        options.extend(self.options(section))
      return options
    else:
      prefix = section + '.'
      try:
        return [prefix + opt for opt in self._data[section].keys()]
      except KeyError:
        return []

  def pop(self, key: str, default: t.Any = NotImplemented) -> t.Any:
    try:
      scope, name = OptionKey.parse(key)
    except ValueError:
      if default is NotImplemented:
        raise KeyError(key)
      return default
    if scope not in self._data:
      if default is NotImplemented:
        raise KeyError(key)
      return default
    if name not in self._data[scope]:
      if default is NotImplemented:
        raise KeyError(key)
      return default
    section = self._data[scope]
    if default is NotImplemented:
      try:
        return section.pop(name)
      except KeyError:
        raise KeyError(key)
    else:
      return section.pop(name, default)

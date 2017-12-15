"""
Reader for TOML configuration files with a little extra for evaluating
`cfg(...)` prefixes in key names. Example:

```toml
[native]
toolkit = "llvm"

['cfg(win32)'.native]
toolkit = "msvc"
```
"""

import collections
import toml
import cfgfilter from './cfgfilter'

OptionKey = collections.namedtuple('OptionKey', 'scope name')


def parse_option_key(s, allow_empty_name=False):
  scope, sep, name = s.rpartition('.')
  if not scope and not sep:
    scope, name = name, ''
  valid = scope and ((sep and name) or allow_empty_name)
  if not valid:
    raise ValueError('invalid option key: {!r}'.format(s))
  return OptionKey(scope, name)


class Configuration:

  def __init__(self):
    self._data = {}
    self._cfg_context = cfgfilter.Context({})

  def add_cfg_property(self, key, value=True):
    self._cfg_context.vars[key] = value

  def data(self):
    return self._data

  def read(self, filename):
    with open(filename, 'r') as fp:
      data = toml.load(fp)
    for key, value in data.keys():
      if key.startswith('cfg(') and key.endswith(')'):
        if not self._cfg_context.eval(key[4:-1]):
          continue
        self._data.update(value)
      else:
        self._data[key] = value

  def __getitem__(self, key):
    try:
      scope, name = parse_option_key(key)
    except ValueError:
      raise KeyError(key)
    if scope not in self._data:
      raise KeyError(key)
    if name not in self._data[scope]:
      raise KeyError(key)
    return self._data[scope][name]

  def __setitem__(self, key, value):
    try:
      scope, name = parse_option_key(key)
    except ValueError:
      raise KeyError(key)
    if scope not in self._data:
      self._data[scope] = {}
    self._data[scope][name] = value

  def __delitem__(self, key: str):
    try:
      scope, name = parse_option_key(key, allow_empty_name=True)
    except ValueError:
      raise KeyError(key)
    if not name:
      del self._data[scope]
    else:
      del self._data[scope][name]

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  def sections(self):
    return self._data.keys()

  def options(self, section=None):
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

  def pop(self, key, default=NotImplemented):
    try:
      scope, name = parse_option_key(key)
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

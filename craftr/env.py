# Copyright (C) 2015  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

class Environment(object):
  ''' This class is a container for configuration values. An instance
  of this class can inherit values from another. Values can be set,
  prepended or appended. Modified values will be generated on demand
  taking the parent `Environment` into account, if present.

  ```python
  >>> parent = Environment(includes=['path/to/include'], defines=['DEBUG'])
  >>> child = parent.subenv(includes__append=['another/include'])
  >>> child.append(defines=['SOME_DEFINE'])
  >>> print(child)
  {'includes': ['path/to/include', 'another/include'], 'defines': ['DEBUG', 'SOME_DEFINE']}
  >>> child['defines'] = []
  >>> print(child)
  {'includes': ['path/to/include', 'another/include'], 'defines': []}
  >>> child.delete(['defines'])
  >>> print(child)
  {'includes': ['path/to/include', 'another/include']}
  >>> del child['defines']
  >>> print(child)
  {'includes': ['path/to/include', 'another/include'], 'defines': ['DEBUG']}
  >>> print(parent)
  {'includes': ['path/to/include'], 'defines': ['DEBUG']}
  ```

  Parameters:
    **values: Passed to `Environment.apply()`
  '''

  # Sentinel object for deleted entries.
  Delete = type('DeleteSentinel', (), {})()

  def __init__(self, **values):
    super().__init__()
    self._values = {}
    self._parent = None
    self.apply(**values)

  def __getitem__(self, key):
    data = self._values.get(key)
    if not data:
      if self._parent:
        return self._parent[key]
      raise KeyError(key)
    elif data[0] == 'delete':
      raise KeyError(key)
    elif data[0] == 'set':
      return data[1]
    elif data[0] in ('append', 'prepend'):
      if self._parent:
        try:
          parent_value = self._parent[key]
        except KeyError:
          return data[1]
        if not isinstance(parent_value, list):
          raise TypeError('parent value for {0!r} is not a list'.format(key))
        if data[0] == 'append':
          return parent_value + data[1]
        else:
          return data[1] + parent_value
      else:
        return data[1]
    else:
      raise RuntimeError('invalid value mode {0!r}'.format(data[0]))

  def __setitem__(self, key, value):
    self.set(**{key: value})

  def __delitem__(self, key):
    ''' Deletes the entry for the specified *key* from this environment
    object _completely_, causing the value to be purely inherited from
    the parent environment. '''

    self._values.pop(key, None)

  def __repr__(self):
    return str(dict(self.items()))

  def subenv(self, *args, **kwargs):
    ''' Create a new `Environment` object that inherits values from
    this environment. Pass the arguments to the `Environment`
    constructor. '''

    env = Environment(*args, **kwargs)
    env._parent = self
    return env

  def set(self, **kwargs):
    ''' Set the specified key/value pairs in the environment. '''

    for key, value in kwargs.items():
      self._values[key] = ('set', value)

  def delete(self, *keys):
    ''' Delete the specified keys from the environment, causing the key
    to be non-existent even if the parent environment provides it. This
    is severely different from `__delitem__()`. '''

    for key in keys:
      self._values[key] = ('delete', Environment.Delete)

  def append(self, *, __is_prepend__=False, **kwargs):
    ''' Append the specified values to the existing values. The
    values passed must always be lists. If there is already a
    value for a specified key, that value must also be a list.
    Note that a key can not be appended and prepended at the
    same time. Calling this function on a key that is already
    being prepended will switch the mode to append.

    The `Environment` stays unmodified when an exception occurs.

    Parameters:
      __is_prepend__: Internal parameter. Setting this to True
          is like calling `prepend()` instead of `append()`.
      **kwargs: The values to append.
    Returns: self
    Raises:
      TypeError: If not all specified values are lists or an
          existing value for a key is not a list.
    '''

    if not all(isinstance(v, list) for v in kwargs.values()):
      raise TypeError('all values must be lists')

    for key, value in kwargs.items():
      # Is there already a value that we have to append to?
      old_data = self._values.get(key, None)
      if old_data and old_data[0] != 'del':
        if not isinstance(old_data[1], list):
          raise TypeError('existing value for {0!r} is not a list'.format(key))
        if __is_prepend__:
          value = value + old_data[1]
        else:
          value = old_data[1] + value
        kwargs[key] = value

    mode = 'prepend' if __is_prepend__ else 'append'
    for key, value in kwargs.items():
      self._values[key] = (mode, value)

    return self

  def prepend(self, **kwargs):
    ''' Exactly like `append()`, but for prepending instead. '''

    return self.append(__is_prepend__=True, **kwargs)

  def apply(self, **kwargs):
    ''' Set, append, prepend or delete keys from the environment
    based on the naming of the keyword arguments. Keys can end with
    `__set`, `__append`, `__prepend` or `__delete` to apply the
    respective action on the key. For the `__delete` method, the
    specified value must be None or `Environment.Delete`.

    If the key ends with none of the supported suffixes, the "set"
    method is applied except if the value for the key is
    `Environment.Delete` in which case the value is deleted. '''

    for key, value in kwargs.items():
      mode = None
      if key.endswith('__set'):
        key = key[:-5]
        mode = 'set'
      elif key.endswith('__append'):
        key = key[:-8]
        mode = 'append'
      elif key.endswith('__prepend'):
        key = key[:-9]
        mode = 'prepend'
      elif key.endswith('__delete'):
        key = key[:-8]
        mode = 'delete'
      if value is Environment.Delete:
        if mode and mode != 'delete':
          raise RuntimeError('Environment.Delete AND mode specified')
        mode = 'delete'
      if not mode:
        mode = 'set'
      if mode == 'delete':
        self.delete(key)
      else:
        getattr(self, mode)(**{key: value})

    return self

  def keys(self):
    if self._parent:
      keys = set(self._parent.keys())
    else:
      keys = set()
    for key, data in self._values.items():
      if data[0] == 'delete':
        keys.discard(key)
      else:
        keys.add(key)
    return keys

  def values(self):
    values = []
    for key in self.keys():
      values.append(self[key])

  def items(self):
    for key in self.keys():
      yield (key, self[key])


  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

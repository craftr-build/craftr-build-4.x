# Copyright (c) 2019 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from nr.collections import abc


class ObjectAsDict(abc.MutableMapping):
  """
  This class wraps an object and exposes its members as mapping.
  """

  def __new__(cls, obj):
    if isinstance(obj, ObjectFromDict):
      return obj._ObjectFromDict__mapping
    return super(ObjectAsDict, cls).__new__(cls)

  def __init__(self, obj):
    self.__obj = obj

  def __repr__(self):
    return 'ObjectAsDict({!r})'.format(self.__obj)

  def __iter__(self):
    return self.keys()

  def __len__(self):
    return len(dir(self.__obj))

  def __contains__(self, key):
    return hasattr(self.__obj, key)

  def __getitem__(self, key):
    try:
      return getattr(self.__obj, key)
    except AttributeError:
      raise KeyError(key)

  def __setitem__(self, key, value):
    setattr(self.__obj, key, value)

  def __delitem__(self, key):
    delattr(self.__obj, key)

  def keys(self):
    return iter(dir(self.__obj))

  def values(self):
    return (getattr(self.__obj, k) for k in dir(self.__obj))

  def items(self):
    return ((k, getattr(self.__obj, k)) for k in dir(self.__obj))

  def get(self, key, default=None):
    return getattr(self.__obj, key, default)

  def setdefault(self, key, value):
    try:
      return getattr(self.__obj, key)
    except AttributeError:
      setattr(self.__obj, key, value)
      return value


class ObjectFromDict(object):
  """
  This class wraps a dictionary and exposes its values as members.
  """

  def __new__(cls, mapping, name=None):
    if isinstance(mapping, ObjectAsDict):
      return mapping._ObjectAsDict__obj
    return super(ObjectFromDict, cls).__new__(cls)

  def __init__(self, mapping, name=None):
    self.__mapping = mapping
    self.__name = name

  def __getattribute__(self, key):
    if key.startswith('_ObjectFromDict__'):
      return super(ObjectFromDict, self).__getattribute__(key)
    try:
      return self.__mapping[key]
    except KeyError:
      raise AttributeError(key)

  def __setattr__(self, key, value):
    if key.startswith('_ObjectFromDict__'):
      super(ObjectFromDict, self).__setattr__(key, value)
    else:
      self.__mapping[key] = value

  def __delattr__(self, key):
    if key.startswith('_ObjectFromDict__'):
      super(ObjectFromDict, self).__delattr__(key)
    else:
      del self.__mapping[key]

  def __dir__(self):
    return sorted(self.__mapping.keys())

  def __repr__(self):
    if self.__name:
      return '<ObjectFromDict name={!r}>'.format(self.__name)
    else:
      return '<ObjectFromDict {!r}>'.format(self.__mapping)


class ValueIterableDict(abc.MutableMapping):
  """
  Just like any other map, but iterating over the map will yield the values
  instead of the keys. This is useful for lookup-maps where the values contain
  the keys that they are associated with in the map.
  """

  def __init__(self, iterable=None, map=None):
    if map is None:
      map = {}
    self._map = map
    if iterable is not None:
      self._map.update(iterable)

  def __repr__(self):
    return '{}({!r})'.format(type(self).__name__, self._map)

  def __len__(self):
    return len(self._map)

  def __iter__(self):
    return iter(self._map.values())

  def __getitem__(self, key):
    return self._map[key]

  def __setitem__(self, key, value):
    self._map[key] = value

  def __delitem__(self, key, value):
    del self._map[key]

  def __getattr__(self, attr):
    return getattr(self._map, attr)

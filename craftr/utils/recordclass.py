# Copyright (C) 2016  Niklas Rosenstein
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


class recordclass_base(object):
  '''
  Base class that provides a namedtuple like interface based on
  the ``__slots__`` parameter.

  .. code:: python

    class MyRecord(recordclass_base):
      __slots__ = 'foo bar ham'.split()

    data = MyRecord('a foo', 42, ham="spam")
  '''

  def __init__(self, *args, **kwargs):
    for key, arg in zip(self.__slots__, args):
      if key in kwargs:
        msg = 'multiple values for argument {0!r}'.format(key)
        raise TypeError(msg)
      kwargs[key] = arg
    for key, arg in kwargs.items():
      setattr(self, key, arg)
    for key in self.__slots__:
      if not hasattr(self, key):
        if key in defaults:
          setattr(self, key, defaults[key])
        else:
          raise TypeError('missing argument {0!r}'.format(key))

  def __repr__(self):
    parts = ['{0}={1!r}'.format(k, v) for k, v in self.items()]
    return '{0}('.format(name) + ', '.join(parts) + ')'

  def __iter__(self):
    for key in self.__slots__:
      yield getattr(self, key)

  def __len__(self):
    return len(self.__slots__)

  def __getitem__(self, index_or_key):
    if isinstance(index_or_key, int):
      return getattr(self, self.__slots__[index_or_key])
    elif isinstance(index_or_key, str):
      if index_or_key not in self.__slots__:
        raise KeyError(index_or_key)
      return getattr(self, index_or_key)
    else:
      raise TypeError('expected int or str')

  def __setitem__(self, index_or_key, value):
    if isinstance(index_or_key, int):
      setattr(self, self.__slots__[index_or_key], value)
    elif isinstance(index_or_key, str):
      if index_or_key not in self.__slots__:
        raise KeyError(index_or_key)
      setattr(self, index_or_key, value)
    else:
      raise TypeError('expected int or str')

  def items(self):
    for key in self.__slots__:
      yield key, getattr(self, key)

  def keys(self):
    return iter(self.__slots__)

  def values(self):
    for key in self.__slots__:
      yield getattr(self, key)

  def _asdict(self):
    return {k: getattr(self, k) for k in self.__slots__}


def recordclass(__name, __fields, **defaults):
  '''
  Creates a new class that can represent a record with the
  specified *fields*. This is equal to a mutable namedtuple.
  The returned class also supports keyword arguments in its
  constructor.

  :param __name: The name of the recordclass.
  :param __fields: A string or list of field names.
  :param defaults: Default values for fields. The defaults
    may list field names that haven't been listed in *fields*.
  '''

  name = __name
  fields = __fields
  fieldset = set(fields)

  if isinstance(fields, str):
    if ',' in fields:
      fields = fields.split(',')
    else:
      fields = fields.split()
  else:
    fields = list(fields)

  for key in defaults.keys():
    if key not in fields:
      fields.append(key)

  class _record(recordclass_base):
    __slots__ = fields
  _record.__name__ = name
  return _record

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

from craftr import environ, path
from tempfile import mkstemp as _mkstemp
from contextlib import contextmanager

import os
import re
import sys

# PATH fiddling --------------------------------------------------------------

def append_path(pth):
  ''' Append *pth* to the `PATH` environment variable. '''

  environ['PATH'] = environ['PATH'] + path.pathsep + pth


def prepend_path(pth):
  ''' Prepend *pth* to the `PATH` environment variable. '''

  environ['PATH'] = pth + path.pathsep + environ['PATH']


def find_program(name):
  """
  Finds the program *name* in the `PATH` and returns the full
  absolute path to it. On Windows, this also takes the `PATHEXT`
  variable into account.


  :param name: The name of the program to find.
  :return: :class:`str` -- The absolute path to the program.
  :raise FileNotFoundError: If the program could not be found in the PATH.
  :raise PermissionError: If a candidate for "name" was found but
    it is not executable.
  """

  if path.isabs(name):
    if not path.isfile(name):
      raise FileNotFoundError(name)
    if not os.access(name, os.X_OK):
      raise PermissionError('{0!r} is not executable'.format(name))
    return name

  iswin = sys.platform.startswith('win32')
  iscygwin = sys.platform.startswith('cygwin')
  if iswin and '/' in name or '\\' in name:
    return path.abspath(name)
  elif iswin and path.sep in name:
    return path.abspath(name)

  if iswin:
    pathext = environ['PATHEXT'].split(path.pathsep)
  elif iscygwin:
    pathext = [None, '.exe']
  else:
    pathext = [None]

  first_candidate = None
  for dirname in environ['PATH'].split(path.pathsep):
    fullname = path.join(dirname, name)
    for ext in pathext:
      extname = (fullname + ext) if ext else fullname
      if path.isfile(extname):
        if os.access(extname, os.X_OK):
          return extname
        if first_candidate is None:
          first_candidate = extname

  if first_candidate:
    raise PermissionError('{0!r} is not executable'.format(first_candidate))
  raise FileNotFoundError(name)


def test_program(name):
  """
  Uses :func:`find_program` to find the path to "name" and returns
  True if it could be found, False otherwise.
  """

  try:
    find_program(name)
  except OSError:
    return False
  return True


@contextmanager
def override_environ(new_environ=None):
  """
  Context-manager that restores the old :data:`environ` on exit.

  :param new_environ: A dictionary that will update the :data:`environ`
    inside the context-manager.
  """

  old_environ = environ.copy()
  try:
    if new_environ:
      environ.update(new_environ)
    yield
  finally:
    environ.clear()
    environ.update(old_environ)


# General Programming Utilities ----------------------------------------------

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

  class _record(object):
    __slots__ = fields

    def __init__(self, *args, **kwargs):
      for key, arg in izip(fields, args):
        if key in kwargs:
          msg = 'multiple values for argument {0!r}'.format(key)
          raise TypeError(msg)
        kwargs[key] = arg
      for key, arg in kwargs.items():
        setattr(self, key, arg)
      for key in fields:
        if not hasattr(self, key):
          if key in defaults:
            setattr(self, key, defaults[key])
          else:
            raise TypeError('missing argument {0!r}'.format(key))

    def __repr__(self):
      parts = ['{0}={1!r}'.format(k, v) for k, v in self.items()]
      return '{0}('.format(name) + ', '.join(parts) + ')'

    def __iter__(self):
      for key in fields:
        yield getattr(self, key)

    def __len__(self):
      return len(fields)

    def items(self):
      for key in fields:
        yield key, getattr(self, key)

    def keys(self):
      return iter(fields)

    def values(self):
      for key in fields:
        yield getattr(self, key)

  _record.__name__ = name
  return _record


slotobject = recordclass  # Backwards compatibility < 1.1.1


def flatten(iterable):
  ''' Given an *iterable* that in turn yields an iterable, this function
  flattens the nested iterables into a single iteration. '''

  for item in iterable:
    yield from item


def unique(iterable):
  ''' Create a list of items in *iterable* without duplicate, preserving
  the order of the elements where it first appeared. '''

  result = []
  for item in iterable:
    if item not in result:
      result.append(item)
  return result


class tempfile(object):
  ''' A better temporary file class where the :meth:`close` function
  does not delete the file but only :meth:`__exit__` does. '''

  def __init__(self, suffix='', prefix='tmp', dir=None, text=False):
    super().__init__()
    self.fd, self.name = _mkstemp(suffix, prefix, dir, text)
    self.fp = os.fdopen(self.fd, 'w' if text else 'wb')

  def __enter__(self):
    return self

  def __exit__(self, *__):
    try:
      self.close()
    finally:
      path.silent_remove(self.name)

  def __getattr__(self, name):
    return getattr(self.fp, name)

  def close(self):
    if self.fp:
      self.fp.close()
      self.fp = None


# Regular Expression Helpers -------------------------------------------------

def gre_search(pattern, subject, mode=0):
  ''' Performs `re.search()` and returns a list of the captured groups,
  *including* the complete matched string as the first group. If the
  regex search was unsuccessful, a list with that many items containing
  None is returned. '''

  pattern = re.compile(pattern, mode)
  ngroups = pattern.groups + 1

  res = pattern.search(subject)
  if not res:
    return [None] * ngroups
  else:
    groups = list(res.groups())
    groups.insert(0, res.group(0))
    return groups

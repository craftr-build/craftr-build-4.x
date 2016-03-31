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

import os
import re
import sys
from tempfile import mkstemp as _mkstemp

# PATH fiddling --------------------------------------------------------------

def append_path(pth):
  ''' Append *pth* to the `PATH` environment variable. '''

  environ['PATH'] = environ['PATH'] + path.pathsep + pth


def prepend_path(pth):
  ''' Prepend *pth* to the `PATH` environment variable. '''

  environ['PATH'] = pth + path.pathsep + environ['PATH']


def find_program(name):
  ''' Finds the program *name* in the `PATH` and returns the full
  absolute path to it. On Windows, this also takes the `PATHEXT`
  variable into account.

  Arguments:
    name: The name of the program to find.
  Returns:
    str: The absolute path to the program.
  Raises:
    FileNotFoundError: If the program could not be found in the PATH. '''

  if path.isabs(name):
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

  for dirname in environ['PATH'].split(path.pathsep):
    fullname = path.join(dirname, name)
    for ext in pathext:
      extname = (fullname + ext) if ext else fullname
      if path.isfile(extname) and os.access(extname, os.X_OK):
        return extname
  raise FileNotFoundError(name)



# General Programming Utilities ----------------------------------------------

def slotobject(cls_name, slots):
  ''' Similar to :func:`collections.namedtuple`, this function creates
  a type object with the attributes specified via the *slots* (a string
  or list of strings) only the type does not inherit from :class:`tuple`
  but insead from :class:`object`. Its attributes can actually be changed.
  Instances of the type can not act as tuples.

  .. code-block:: python

    >>> from craftr.utils import slotobject
    >>> File = slotobject('File', 'name arc_name')
    >>> File('foo', 'subdir/foo')
    <File name='foo' arc_name='subdir/foo'>
  '''

  if isinstance(slots, str):
    if ',' in slots:
      slots = slots.split(',')
    else:
      slots = slots.split(' ')
  slots_set = frozenset(slots)
  assert len(slots_set) == len(slots)

  def __init__(self, *args, **kwargs):
    # Fill the args matching the slots in kwargs.
    if len(args) > len(slots):
      raise TypeError('{0}() expected {1} positional arguments, got {2}'.format(
        cls_name, len(slots), len(args)))
    for key in kwargs:
      if key not in slots_set:
        raise TypeError('{0}() unexpected keyword argument \'{1}\''.format(
          cls_name, key))
    for key, arg in zip(slots, args):
      if key in kwargs:
        raise TypeError('{0}() duplicate parameter for argument \'{1}\''.format(
          cls_name, key))
      kwargs[key] = arg
    if len(kwargs) != len(slots):
      raise TypeError('{0}() missing arguments'.format(cls_name))
    for key, value in kwargs.items():
      setattr(self, key, value)

  def __str__(self):
    parts = []
    for key in slots:
      parts.append('{0}={1!r}'.format(key, getattr(self, key)))
    result = '<{0}'.format(cls_name)
    if parts:
      result += ' ' + ' '.join(parts)
    return result + '>'

  return type(cls_name, (object,), {
    '__init__': __init__,
    '__slots__': slots,
    '__str__': __str__,
  })


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

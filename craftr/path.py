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

from craftr import module, session
from os.path import *
from os import sep, pathsep, curdir, pardir, getcwd
from tempfile import mkstemp as _mkstemp

import collections
import ctypes
import errno
import functools
import glob2
import os
import shutil
import sys

def _iter_applicable(func):
  '''
  Decorator for functions that process a string argument. The returned
  function will operate the same on a single string, but can be applied
  recursively on an iterable of strings or nested iterables and return
  the same nested structure as lists where each non-iterable is processed
  by the wrapped function.
  '''

  @functools.wraps(func)
  def wrapper(subject, *args, **kwargs):
    if isinstance(subject, collections.Iterable) and not isinstance(subject, str):
      return [wrapper(x, *args, **kwargs) for x in subject]
    else:
      return func(subject, *args, **kwargs)

  return wrapper


split = _iter_applicable(os.path.split)
dirname = _iter_applicable(os.path.dirname)
basename = _iter_applicable(os.path.basename)


def isglob(path):
  ''' Returns True if *path* is a glob-able pattern, False if not. '''

  return any(x in path for x in '*?')


def autoglob(path, parent=None):
  ''' Returns `glob(path)` if *path* is actually a glob-style pattern.
  If it is not, it will return `[path]` as is, not checking wether it
  exists or not. '''

  if isglob(path):
    return glob(path, parent=parent)
  else:
    return [path]


def glob(*patterns, exclude=None, parent=None):
  ''' Wrapper for `glob2.glob()` that accepts an arbitrary number of
  patterns and matches them. The paths are normalized with `normpath()`.
  If called from within a module, relative patterns are assumed relative
  to the modules parent directory.

  If *exclude* is specified, it must be a string or a list of strings
  that is/contains glob patterns or filenames to be removed from the
  result before returning.'''

  if not parent and module:
    parent = module.project_dir

  result = []
  for pattern in patterns:
    if not isabs(pattern):
      pattern = join(parent, pattern)
    result += glob2.glob(normpath(pattern))

  if isinstance(exclude, str):
    exclude = [exclude]
  if exclude is not None:
    for pattern in exclude:
      if not isabs(pattern):
        pattern = join(parent, pattern)
      if not isglob(pattern):
        result.remove(normpath(pattern))
      else:
        for item in glob2.glob(normpath(pattern)):
          result.remove(item)

  return result


def listdir(path, abs=True):
  ''' This version of `os.listdir` yields absolute paths. '''

  if abs:
    return (os.path.join(path, x) for x in os.listdir(path))
  else:
    return iter(os.listdir(path))


def commonpath(paths):
  ''' Returns the longest sub-path of each pathname in the sequence
  *paths*. Raises `ValueError` if *paths* is empty or contains both
  relative and absolute pathnames. If there is only one item in *paths*,
  the parent directory is returned.'''

  if not paths:
    raise ValueError('paths is empty')
  parts = []
  has_abs = None
  for path in paths:
    if not os.path.isabs(path):
      if has_abs is None:
        has_abs = False
      elif has_abs:
        raise ValueError('paths contains relative and absolute pathnames')
    else:
      if has_abs is None:
        has_abs = True
      elif not has_abs:
        raise ValueError('paths contains relative and absolute pathnames')

    path = normpath(path)
    parts.append(path.split(os.sep))

  if len(parts) == 1:
    return dirname(os.sep.join(parts[0]))
  common = parts[0]
  for elements in parts[1:]:
    if len(elements) < len(common):
      common = common[:len(elements)]
    for index, elem in enumerate(elements):
      if index >= len(common):
        break
      if elem != common[index]:
        common = common[:index]
        break
      if not common:
        break

  common = os.sep.join(common)
  if not has_abs:
    common = os.path.relpath(common)
  return common


def normpath(path, parent_dir=None, abs=True):
  ''' Normalizes a filesystem path. Also expands user variables.
  If a *parent_dir* is specified, a relative path is considered
  relative to that directory and converted to an absolute path.
  The default parent directory is the current working directory.

  *path* may be an iterable other than a string in which case the
  function is applied recursively to all its items and a list is
  returned instead of a string.

  If *abs* is True, the path is returned as an absolute path
  always, otherwise the path is returned in its original structure.'''

  if isinstance(path, str):
    path = os.path.expanduser(path)
    if abs and not os.path.isabs(path):
      if parent_dir is None:
        parent_dir = os.getcwd()
      path = os.path.join(parent_dir, path)
    return os.path.normpath(path)
  elif isinstance(path, collections.Iterable):
    result = []
    for item in path:
      result.append(normpath(item, parent_dir))
    return result
  else:
    raise TypeError('normpath() expected string or iterable')

@_iter_applicable
def addprefix(subject, prefix):
  '''
  Given a filename, this function will prepend the specified prefix
  to the base of the filename and return it. *filename* may be an iterable
  other than a string in which case the function is applied recursively
  and a list is being returned instead of a string.

  __Important__: This is *not* the directy equivalent of `addsuffix()`
  as it considered *subject* to be a filename and appends the *prefix*
  only to the files base name.
  '''

  if not prefix:
    return subject
  dir_, base = split(subject)
  return join(dir_, prefix + base)


@_iter_applicable
def addsuffix(subject, suffix, replace=False):
  '''
  Given a string, this function appends *suffix* to the end of
  the string and returns the new string.

  *subject* may be an iterable other than a string in which case the
  function will be applied recursively on all its items and a list is
  being returned instead of a string.

  If the *replace* argument is True, the suffix will be replaced
  instead of being just appended. Make sure to include a period in
  the *suffix* parameter value.
  '''

  if not suffix and not replace:
    return subject
  if replace:
    subject = rmvsuffix(subject)
  if suffix:
    subject += suffix
  return subject


def setsuffix(subject, suffix):
  '''
  Remove the existing suffix from *subject* and add *suffix*
  instead. The *suffix* must contain the dot at the beginning.
  '''

  return addsuffix(subject, suffix, replace=True)


@_iter_applicable
def rmvsuffix(subject):
  '''
  Given a filename, this function removes the the suffix of the
  filename and returns it. If the filename had no suffix to begin with,
  it is returned unchanged.

  *subject* may be an iterable other than a string in which case the
  function is applied recursively to its items and a list is returned
  instead of a string.
  '''

  index = subject.rfind('.')
  if index > subject.replace('\\', '/').rfind('/'):
    subject = subject[:index]
  return subject


def move(filename, basedir, newbase):
  ''' Given a filename and two directory names, this function generates
  a new filename which is constructed from the relative path of the
  filename and the first directory and the joint of this relative path
  with the second directory.

  This is useful to generate a new filename in a different directory
  based on another. Craftr uses this function to generate object
  filenames.

  Example:

      >>> move('src/main.c', 'src', 'build/obj')
      build/obj/main.c

  *path* may be an iterable other than a string in which case the
  function is applied recursively to all its items and a list is
  returned instead of a string. '''

  if isinstance(filename, str):
    rel = relpath(filename, basedir)
    if rel == os.curdir or rel.startswith(os.pardir):
      raise ValueError('pathname not a subpath of basedir', filename, basedir)
    return join(newbase, relpath(filename, basedir))
  elif isinstance(filename, collections.Iterable):
    result = []
    for item in filename:
      result.append(move(item, basedir, newbase))
    return result
  else:
    raise TypeError('move() expected string or iterable')


def local(path):
  '''
  Given a path relative to the current module's project directory,
  this function returns a normalized absolute path. Just like many
  of the path functions, *path* can also be alist.

  .. note::

    Can only be called from a module context (ie. from inside a
    Craftr module).
  '''

  return normpath(path, module.project_dir)


def buildlocal(path):
  '''
  Given a relative path, this function returns an absolute version
  assuming the path is relative to to current module's build
  directory.

  .. note::

    Can only be called from a module context (ie. from inside a
    Craftr module).
  '''

  return join(module.project_name, path)


def projectlocal(path):
  '''
  Given a relative path, this function returns an absolute path
  assuming it is relative to the :attr:`Session.cwd` path, that
  is the working directory that Craftr is being invoked from
  OR, if specified, the project directory that is overwritten
  using the ``-p`` option.

  .. note::

    Can only be called from a session context (ie. from inside
    a ``craftrc.py`` file or a Craftr module).
  '''

  return normpath(path, session.cwd)


def iter_tree(dirname, depth=1):
  ''' Iterates over all files in *dirname* and its sub-directories up
  to the specified *depth*. If *dirname* is a list, this scheme will be
  applied for all items in the list. '''

  if not isinstance(dirname, (tuple, list)):
    dirname = [dirname]

  def recursion(dirname, depth):
    try:
      items = os.listdir(dirname)
    except OSError:
      return
    for path in items:
      path = os.path.join(dirname, path)
      yield path
      if depth > 0 and os.path.isdir(path):
        yield from recursion(path, depth - 1)

  for path in dirname:
    yield from recursion(path, depth)


def relpath(path, start='.', only_sub=False):
  ''' Like the original `os.path.relpath()` function, but with the
  *only_sub* parameter. If *only_sub* is True and *path* is not a
  subpath of *start*, the *path* is returned unchanged. '''

  if not only_sub:
    return os.path.relpath(path, start)
  else:
    try:
      res = os.path.relpath(path, start)
    except ValueError:
      return path  # On windows if drive letters don't match
    if res.startswith(pardir):
      return path
    return res


def split_parts(path):
  ''' Splits *path* into a list of its parts. '''

  result = []
  path = normpath(path, abs=False)
  path, base = split(path)
  while base:
    result.append(base)
    path, base = split(path)

  result.reverse()
  return result


def makedirs(path):
  ''' Simple `os.makedirs()` clone that does not error if *path*
  is already an existing directory. '''

  if not os.path.isdir(path):
    os.makedirs(path)


def get_long_path_name(path):
  ''' On Windows, this function returns the correct capitalization
  for *path*. On all other systems, this returns *path* unchanged. '''

  # xxx: what about cygwin?
  if sys.platform.startswith('win32'):
    # Thanks to http://stackoverflow.com/a/3694799/791713
    assert sys.platform.startswith('win32')
    buf = ctypes.create_unicode_buffer(len(path) + 1)
    GetLongPathNameW = ctypes.windll.kernel32.GetLongPathNameW
    res = GetLongPathNameW(path, buf, len(path) + 1)
    if res == 0 or res > 260:
      return path
    else:
      return buf.value
  else:
    return path


def silent_remove(filename, is_dir=False):
  '''
  Remove the file *filename* if it exists and be silent if it
  does not. Returns True if the file was removed, False if it did
  not exist. Raises an error in all other cases.

  :param filename: The path to the file or directory to remove.
  :param is_dir: If True, remove recursive (for directories).
  '''

  try:
    if is_dir:
      shutil.rmtree(filename)
    else:
      os.remove(filename)
  except OSError as exc:
    if exc.errno != errno.ENOENT:
      raise
    return False
  else:
    return True


class tempfile(object):
  r'''
  A better temporary file class where the :meth:`close` function
  does not delete the file but only :meth:`__exit__` does. Obviously,
  this allows you to close the file and re-use it with some other
  processing before it finally gets deleted.

  This is especially important on Windows because apparently another
  process can't read the file while it's still opened in the process
  that created it.

  .. code:: python

    from craftr import path, shell
    with path.tempfile(suffix='c', text=True) as fp:
      fp.write('#include <stdio.h>\nint main() { }\n')
      fp.close()
      shell.run(['gcc', fp.name])

  :param suffix: The suffix of the temporary file.
  :param prefix: The prefix of the temporary file.
  :param dir: Override the temporary directory.
  :param text: True to open the file in text mode. Otherwise, it
    will be opened in binary mode.
  '''

  def __init__(self, suffix='', prefix='tmp', dir=None, text=False):
    self.fd, self.name = _mkstemp(suffix, prefix, dir, text)
    self.fp = os.fdopen(self.fd, 'w' if text else 'wb')

  def __enter__(self):
    return self

  def __exit__(self, *__):
    try:
      self.close()
    finally:
      silent_remove(self.name)

  def __getattr__(self, name):
    return getattr(self.fp, name)

  def close(self):
    if self.fp:
      self.fp.close()
      self.fp = None

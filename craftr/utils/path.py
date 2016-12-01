# The Craftr build system
# Copyright (C) 2016  Niklas Rosenstein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from craftr.utils import argspec
from os import sep, pathsep, curdir, pardir, getcwd
from os.path import exists, isdir, isfile, isabs, abspath as abs
from os.path import join, split, dirname, basename, expanduser

import ctypes
import errno
import glob2
import os
import shutil
import tempfile as _tempfile

curdir_sep = curdir + sep
pardir_sep = pardir + sep


def rel(path, parent=None, nopar=False):
  """
  Like :func:`os.path.relpath`, but the *nopar* parameter can be set to return
  an absolute path if the relative path would create a path element that
  references a parent directory (`..`) or current directory (``.``).
  """

  try:
    res = os.path.relpath(path, parent)
  except ValueError:
    if nopar:
      return abs(path)
    raise
  else:
    if not issub(res):
      return abs(path)
    return res

def norm(path, parent=None):
  """
  Normalizes the specified *path*. This turns it into an absolute path and
  removes all superfluous path elements. Similar to :func:`os.path.normpath`,
  but accepts a *parent* argument which is considered when *path* is relative.
  """

  if not isabs(path):
    path = join(parent or getcwd(), path)
  return canonical(path)

def canonical(path):
  """
  A synonym for :meth:`os.path.normpath`.
  """

  return os.path.normpath(path)

def glob(patterns, parent=None, excludes=(), include_dotfiles=False):
  """
  Wrapper for :func:`glob2.glob` that accepts an arbitrary number of
  patterns and matches them. The paths are normalized with :func:`norm`.

  Relative patterns are automaticlly joined with *parent*. If the
  parameter is omitted, it defaults to the currently executed build
  scripts project directory.

  If *excludes* is specified, it must be a string or a list of strings
  that is/contains glob patterns or filenames to be removed from the
  result before returning.

  .. note::

    Every file listed in *excludes* will only remove **one** item from
    the result list that was generated from *patterns*. Thus, if you
    want to exclude some files with a pattern except for a specific file
    that would also match that pattern, simply list that file another
    time in the *patterns*.

  :param patterns: A list of glob patterns or filenames.
  :param parent: The parent directory for relative paths.
  :param excludes: A list of glob patterns or filenames.
  :param include_dotfiles: If True, ``*`` and ``**`` can also capture
    file or directory names starting with a dot.
  :return: A list of filenames.
  """

  argspec.validate('patterns', patterns, {'type': [list, tuple]})
  argspec.validate('excludes', excludes, {'type': [list, tuple]})
  argspec.validate('parent', parent, {'type': [None, str]})

  if not parent:
    parent = getcwd()

  result = []
  for pattern in patterns:
    if not isabs(pattern):
      pattern = join(parent, pattern)
    result += glob2.glob(norm(pattern))

  for pattern in excludes:
    if not isabs(pattern):
      pattern = join(parent, pattern)
    pattern = norm(pattern)
    if not isglob(pattern):
      result.remove(pattern)
    else:
      for item in glob2.glob(pattern):
        result.remove(item)

  return result

def isglob(path):
  """
  :param path: The string to check
  :return bool: True if the path is a glob pattern, False otherwise.
  """

  return '*' in path or '?' in path

def issub(path):
  """
  Returns True if *path* is a relative path that does not point outside
  of its parent directory or is equal to its parent directory (thus, this
  function will also return False for a path like ``./``).
  """

  if isabs(path):
    return False
  if path.startswith(curdir_sep) or path.startswith(pardir_sep):
    return False
  return True

def maybedir(path):
  """
  Returns True if *path* ends with a separator. This information can be used
  to interpret a path as a directory or a filename only from its
  representation.

  .. code:: python

    >>> maybedir('foobar/')
    True
    >>> maybedir('foo/bar')
    False
  """

  if os.name == 'nt':
    return path.endswith('/') or path.endswith('\\')
  return path.endswith('/')

def addprefix(subject, prefix):
  """
  Adds the specified *prefix* to the last path element in *subject*.
  If *prefix* is a callable, it must accept exactly one argument, which
  is the last path element, and return a modified value.
  """

  if not prefix:
    return subject
  dir_, base = split(subject)
  if callable(prefix):
    base = prefix(base)
  else:
    base = prefix + base
  return join(dir_, base)

def addsuffix(subject, suffix, replace=False):
  """
  Adds the specified *suffix* to the *subject*. If *replace* is True, the
  old suffix will be removed first. If *suffix* is callable, it must accept
  exactly one argument and return a modified value.
  """

  if not suffix and not replace:
    return subject
  if replace:
    subject = rmvsuffix(subject)
  if suffix and callable(suffix):
    subject = suffix(subject)
  elif suffix:
    subject += suffix
  return subject

def setsuffix(subject, suffix):
  """
  Synonymous for passing the True for the *replace* parameter in
  :func:`addsuffix`.
  """
  return addsuffix(subject, suffix, replace=True)

def rmvsuffix(subject):
  """
  Remove the suffix from *subject*.
  """

  index = subject.rfind('.')
  if index > subject.replace('\\', '/').rfind('/'):
    subject = subject[:index]
  return subject

def makedirs(path):
  """
  Like :func:`os.makedirs`, but this function does not raise an exception
  when the directory at *path* already exists.
  """

  try:
    os.makedirs(path)
  except FileExistsError:
    pass  # intentional

def remove(path, recursive=False, silent=False):
  """
  Like :func:`os.remove`, but the *silent* parmaeter can be specified to
  prevent the function from raising an exception if the *path* could not be
  removed. Also, the *recursive* parameter allows you to use this function
  to remove directories as well. In this case, :func:`shutil.rmtree` is
  used.
  """

  try:
    if recursive and isdir(path):
      shutil.rmtree(path)
    else:
      os.remove(path)
  except OSError as exc:
    if not silent or exc.errno != errno.ENOENT:
      raise

def get_long_path_name(path):
  """
  This function is important when using Craftr on platforms with
  case-insenstive filesystem, such as Windows. It returns the correct
  capitalization for *path*, given that it exists. For other platforms,
  the *path* is returned as-is.

  If *path* does not exist, it is returned unchanged in any case.
  """

  # TODO: Is Cygwin case-insenstive as well?

  if os.name == 'nt':
    # Thanks to http://stackoverflow.com/a/3694799/791713
    buf = ctypes.create_unicode_buffer(len(path) + 1)
    GetLongPathNameW = ctypes.windll.kernel32.GetLongPathNameW
    res = GetLongPathNameW(path, buf, len(path) + 1)
    if res == 0 or res > 260:
      return path
    else:
      return buf.value

  return path

def transition(filename, oldbase, newbase):
  """
  Translates the *filename* from the directory *oldbase* to the new
  directory *newbase*. This is identical to finding the relative path
  of *filename* to *oldbase* and joining it with *newbase*. The #filename
  must be a sub-path of *oldbase*.

  .. code:: python

    >>> transition('src/main.c', 'src', 'build/obj')
    build/obj/main.c
  """

  rel_file = rel(filename, oldbase, nopar=True)
  if isabs(rel_file):
    raise ValueError("filename must be a sub-path of oldbase", filename, oldbase)
  return join(newbase, rel_file)

def common(paths):
  """
  Returns the longest sub-path of each path in the *paths* list. If *paths* is
  empty, contains mixed absolute/relative paths or the paths have no common
  path, a :class:`ValueError` is raised.

  If there is only one element in *paths*, its parent directory is returned.
  """

  if not paths:
    raise ValueError('paths is empty')

  parts = []
  has_abs = None
  for path in paths:
    if not isabs(path):
      if has_abs is None:
        has_abs = False
      elif has_abs:
        raise ValueError('paths contains relative and absolute pathnames')
    else:
      if has_abs is None:
        has_abs = True
      elif not has_abs:
        raise ValueError('paths contains relative and absolute pathnames')

    path = norm(path)
    parts.append(path.split(sep))

  if len(parts) == 1:
    path = dirname(sep.join(parts[0]))
    if not has_abs:
      path = rel(path)
    return path

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

  if not common:
    raise ValueError("no common path")

  common = sep.join(common)
  if not has_abs:
    common = rel(common)
  return common

def easy_listdir(directory):
  """
  A friendly version of :func:`os.listdir` that does not error if the
  *directory* doesn't exist.
  """

  try:
    return os.listdir(directory)
  except OSError as exc:
    if exc.errno != errno.ENOENT:
      raise
  return []

class tempfile(object):
  """
  A better temporary file class where the #close() function does not delete
  the file but only #__exit__() does. Obviously, this allows you to close
  the file and re-use it with some other processing before it finally gets
  deleted.

  This is especially important on Windows because apparently another
  process can't read the file while it's still opened in the process
  that created it.

  ```python
  from craftr.tools import tempfile
  with tempfile(suffix='c', text=True) as fp:
    fp.write('#include <stdio.h>\nint main() { }\n')
    fp.close()
    shell.run(['gcc', fp.name])
  ```

  @param suffix: The suffix of the temporary file.
  @param prefix: The prefix of the temporary file.
  @param dir: Override the temporary directory.
  @param text: True to open the file in text mode. Otherwise, it
    will be opened in binary mode.
  """

  def __init__(self, suffix='', prefix='tmp', dir=None, text=False):
    self.fd, self.name = _tempfile.mkstemp(suffix, prefix, dir, text)
    self.fp = os.fdopen(self.fd, 'w' if text else 'wb')

  def __enter__(self):
    return self

  def __exit__(self, *__):
    try:
      self.close()
    finally:
      remove(self.name, silent=True)

  def __getattr__(self, name):
    return getattr(self.fp, name)

  def close(self):
    if self.fp:
      self.fp.close()
      self.fp = None

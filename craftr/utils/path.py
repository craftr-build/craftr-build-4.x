# Copyright (C) 2015 Niklas Rosenstein
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

__all__ = (
  'join', 'split', 'dirname', 'basename', 'normpath', 'relpath',
  'prefix', 'suffix', 'move', 'glob',
)

import collections
import os
from glob2 import glob
from os.path import join, split, dirname, basename, relpath


def normpath(path, parent_dir=None):
  ''' Normalizes a filesystem path. Also expands user variables.
  If a *parent_dir* is specified, a relative path is considered
  relative to that directory and converted to an absolute path.
  The default parent directory is the current working directory.

  *path* may be an iterable other than a string in which case the
  function is applied recursively to all its items and a list is
  returned instead of a string. '''

  if isinstance(path, str):
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
      if parent_dir is None:
        parent_dir = os.getcwd()
      path = os.path.join(parent_dir, path)
    if os.name == 'nt':
      path = path.lower()
    return os.path.normpath(path)
  elif isinstance(path, collections.Iterable):
    result = []
    for item in path:
      result.append(normpath(item, parent_dir))
    return result
  else:
    raise TypeError('normpath() expected string or iterable')


def prefix(filename, text):
  ''' Given a filename, this function will prepend the specified prefix
  to the base of the filename and return it. *filename* may be an iterable
  other than a string in which case the function is applied recursively
  and a list is being returned instead of a string. '''

  if not text:
    return filename

  if isinstance(filename, str):
    dir_, base = split(filename)
    return join(dir_, text + base)
  elif isinstance(filename, collections.Iterable):
    result = []
    for item in filename:
      result.append(prefix(item, text))
    return result
  else:
    raise TypeError('prefix() expected string or iterable')


def suffix(filename, text, append=False):
  ''' Given a filename, this function replaces its suffix with the
  specified one or appends the specified suffix directly without any
  replacements based on the value of the *append* parameter.

  If the suffix is to be replaced, this function will ensure that there
  is a dot separating the files base name and the specified new suffix.

  *filename* may be an iterable other than a string in which case the
  function will be applied recursively on all its items and a list is
  being returned instead of a string. '''

  if append and not text:
    return filename

  if isinstance(filename, str):
    index = filename.rfind('.')
    if append:
      filename += text
    else:
      if index > filename.replace('\\', '/').rfind('/'):
        filename = filename[:index]
      if text:
        if not text.startswith('.'):
          text = '.' + text
        filename += text
    return filename
  elif isinstance(filename, collections.Iterable):
    result = []
    for item in filename:
      result.append(suffix(item, text, append))
    return result
  else:
    raise TypeError('suffix() expected string or iterable')


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
    return join(newbase, relpath(filename, basedir))
  elif isinstance(filename, collections.Iterable):
    result = []
    for item in filename:
      result.append(move(item, basedir, newbase))
    return result
  else:
    raise TypeError('move() expected string or iterable')


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


def listdir_abs(dirname):
  ''' Like `os.listdir()`, but yields absolute paths rather than only
  the basename of the items in the directory. '''

  for name in os.listdir(dirname):
    yield os.path.join(dirname, name)

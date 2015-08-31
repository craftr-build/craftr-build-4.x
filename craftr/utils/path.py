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

import os
from os.path import join, split, dirname, basename, relpath
from glob2 import glob


def normpath(path, parent_dir=None):
  path = os.path.expanduser(path)
  if not os.path.isabs(path):
    if parent_dir is None:
      parent_dir = os.getcwd()
    path = os.path.join(parent_dir, path)
  if os.name == 'nt':
    path = path.lower()
  return os.path.normpath(path)


def prefix(filename, prefix):
  ''' Adds the specified *prefix* to the basename of the *filename*
  and returns the new filename. '''

  dir_, base = split(filename)
  return join(dir_, prefix + base)


def suffix(filename, suffix):
  ''' Change the suffix of the *filename* to *suffix*. The suffix will
  be removed if *suffix* is an empty string or None. '''

  index = filename.rfind('.')
  if index > filename.replace('\\', '/').rfind('/'):
    filename = filename[:index]
  if suffix:
    if not suffix.startswith('.'):
      suffix = '.' + suffix
    filename += suffix
  return filename


def move(files, basedir, newbase, suffix=None):
  ''' Replaces the base directory of all filenames in the *files* list
  with the *newbase* and returns a new list. Optionally, the suffix of
  all files can be changed by specifying the *suffix* argument. '''

  result = []
  for filename in files:
    rel = relpath(filename, basedir)
    if suffix is not None:
      if callable(suffix):
        rel = suffix(rel)
      else:
        rel = globals()['suffix'](rel, suffix)
    result.append(os.path.join(newbase, rel))
  return result


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

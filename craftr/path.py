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

from craftr import module
from os.path import join, split, dirname, basename, isabs, isfile, isdir, exists

import os
import glob2


def glob(*patterns):
  ''' Wrapper for `glob2.glob()` that accepts an arbitrary number of
  patterns and matches them. The paths are normalized with `normpath()`.
  If called from within a module, relative patterns are assumed relative
  to the modules parent directory. '''

  result = []
  for pattern in patterns:
    if module and not isabs(pattern):
      pattern = join(module.project_dir, pattern)
    result += [normpath(x) for x in glob2.glob(normpath(pattern))]
  return result


def normpath(path):
  ''' Normalize a filesystem path. This implementation is more
  consistent than `os.path.normpath()`. '''

  path = os.path.normpath(os.path.abspath(path))
  if os.name == 'nt':
    path = path.lower()
  return path


def listdir(path):
  ''' This version of `os.listdir` yields absolute paths. '''

  return (os.path.join(path, x) for x in os.listdir(path))

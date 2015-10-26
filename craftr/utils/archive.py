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
''' Utilities for working with archive files. '''

import os
import errno
import zipfile
from craftr.logging import clear_line


def build(filename, base_dir, include=(), exclude=(), optional=(),
    prefix=None, quiet=False):
  ''' Build a ZIP archive at *filename* and include the specified files.
  The *base_dir* is stripped from the absolute filenames to find the
  arcname. Also, if a relative path is specified in *include*, *exclude*
  or *optional*, *base_dir* is assumed to be the parent directory. If
  a glob-character (ie. ? or *) is found in one of the items specified
  for *include*, *exclude* and *optional*, they are globbed directly.
  Also, a directory name will include all files in it. '''

  def expand(filelist):
    result = set()
    for item in lists.autoexpand(filelist):
      if not os.path.isabs(item):
        item = path.normpath(os.path.join(base_dir, item))
      if os.path.isdir(item):
        result |= set(path.glob(path.join(item, '**')))
      else:
        result |= set(path.autoglob(item))
    return set(map(path.normpath, result))

  files = expand(include) - expand(exclude)
  optional = expand(optional) - files

  for fn in files:
    if not os.path.exists(fn):
      raise OSError(errno.ENOENT, 'No such file or directory: {!r}'.format(fn))
  for fn in optional:
    if os.path.exists(fn):
      files.add(fn)

  if not files:
    raise ValueError('no files to build an archive from')

  zf = zipfile.ZipFile(filename, 'w')
  for fn in files:
    arcname = path.relpath(fn, base_dir).replace('\\', '/')
    if arcname == os.curdir or arcname.startswith(os.pardir):
      raise ValueError('pathname not a subdir of basedir', fn, base_dir)
    if prefix:
      arcname = prefix + '/' + arcname
    if not quiet:
      clear_line()
      print('writing {!r}... '.format(arcname), end='')
    zf.write(fn, arcname)
    if not quiet:
      print('done.', end='')
  zf.close()
  if not quiet:
    clear_line()
    print('{} files compressed in {!r}'.format(len(files), filename))

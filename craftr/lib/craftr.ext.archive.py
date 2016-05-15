# -*- mode: python -*-
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

__all__ = ['Archive']

from craftr import *
from craftr.utils import slotobject
from fnmatch import fnmatch

import zipfile


class Archive(object):
  ''' Helper class to build and a list of files for an archive
  and then create that archive from that list. If no *name* is
  specified, it is derived from the *prefix*. The *format* must
  be ``'zip'`` for now. '''

  File = slotobject('File', 'name arc_name')

  def __init__(self, name = None, base_dir = None, prefix = None, format = 'zip'):
    assert format == 'zip', "format must be 'zip' for now"
    if not name:
      if not prefix:
        raise TypeError('neither name nor prefix argument specified')
      name = prefix + '.' + format
    if prefix and not prefix.endswith('/'):
      prefix += '/'
    self._files = []
    self._base_dir = base_dir or module.project_dir
    self._prefix = prefix
    self.name = name

  def add(self, name, rel_dir = None, arc_name = None, parts = None):
    ''' Add a file, directory or `Target` to the archive file list.
    If *parts* is specified, it must be a number which specifies how
    many parts of the arc name are kept from the right.

    .. note:: *name* can be a filename, the path to a directory,
      a glob pattern or list. Note that a directory will be globbed
      for its contents and will then be added recursively. A glob
      pattern that yields a directory path will add that directory. '''

    if arc_name and parts:
      raise TypeError('arc_name conflicts with parts')

    def _raise_arc():
      if arc_name:
        raise TypeError('arc_name can only be specified for a single file')

    if not rel_dir:
      rel_dir = self._base_dir
    if isinstance(name, (tuple, list)):
      _raise_arc()
      [self.add(path.abspath(x), rel_dir, None, parts) for x in name]
    elif isinstance(name, str):
      if not path.isabs(name):
        name = path.local(name)
      # xxx: make sure *name* is a subpath of *rel_dir*
      if path.isglob(name):
        _raise_arc()
        self.add(path.glob(name), rel_dir, None, parts)
      elif path.isdir(name):
        _raise_arc()
        self.add(path.glob(path.join(name, '*')), rel_dir, None, parts)
      else:
        if not path.isfile(name):
          raise FileNotFoundError(name)
        name = path.get_long_path_name(name)
        if parts:
          assert not arc_name
          path_parts = path.split_path(name)
          arc_name = path.sep.join(path_parts[-parts:])
        if not arc_name:
          arc_name = path.relpath(name, rel_dir)
          if path.sep != '/':
            arc_name = arc_name.replace(path.sep, '/')
          # Make sure the arc_name contains no par-dirs.
          # xxx: Issues with other platforms here that don't use .. ?
          while arc_name.startswith('..'):
            arc_name = arc_name[3:]
        if self._prefix:
          arc_name = self._prefix + arc_name
        name = path.get_long_path_name(name)
        file = Archive.File(name, arc_name)
        self._files.append(file)
    else:
      raise TypeError('name must be str/list/tuple')

  def exclude(self, filter):
    ''' Remove all files in the Archive's file list that match the
    specified *filter*. The filter can be a string, in which case it
    is applied with :func:`fnmatch` or a function which accepts a single
    argument (the filename). '''

    if isinstance(filter, str):
      def wrapper(pattern):
        return lambda x: fnmatch(x, pattern)
      filter = wrapper(filter)

    self._files = [file for file in self._files if not filter(file.name)]

  def rename(self, old_arcname, new_arcname):
    ''' Rename the *old_arcname* to *new_arcname*. This will take
    folders into account. '''

    old_arcname_dir = old_arcname
    if not old_arcname.endswith('/'):
      old_arcname_dir += '/'
    new_arcname_dir = new_arcname
    if not new_arcname_dir.endswith('/'):
      new_arcname_dir += '/'

    for file in self._files:
      if file.arc_name == old_arcname:
        assert new_arcname
        file.arc_name = new_arcname
      elif file.arc_name.startswith(old_arcname_dir):
        file.arc_name = file.arc_name[len(old_arcname_dir):]
        if new_arcname:
          file.arc_name = new_arcname_dir + file.arc_name

  def save(self):
    ''' Save the archive. '''

    zf = zipfile.ZipFile(self.name, 'w')
    for file in self._files:
      zf.write(file.name, file.arc_name)
    zf.close()

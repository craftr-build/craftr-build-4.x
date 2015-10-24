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

from . import dis
from . import ident
from . import lists
from . import path
from . import proxy
from . import shell
import os
import sys
import errno
import craftr
import collections
import zipfile


class DataEntity(object):
  ''' Container for data of a module or a script. '''

  def __init__(self, entity_id):
    super().__init__()
    self.__entity_id__ = entity_id

  def __repr__(self):
    return '<DataEntity {0!r}>'.format(self.__entity_id__)


def singleton(x):
  ''' Decorator for a singleton class or function. The class or
  function will be called and the result returned. '''

  return x()


def accept_keys(dictionary, keys, name='key'):
  ''' This function ensures that the *dictionary* only contains the
  specified *keys*. *keys* can be a string in which case it is split
  by whitespace or comma. A `TypeError` is raised if an invalid key
  is detected. '''

  if isinstance(keys, str):
    if ',' in keys:
      keys = keys.split(',')
    else:
      keys = keys.split()
  invalids = set(dictionary.keys()).difference(set(keys))
  if invalids:
    key = next(iter(invalids))
    raise TypeError('unexpected {} {!r}'.format(name, key))


def get_calling_module(module=None):
  ''' Call this from a rule function to retrieve the craftr module that
  was calling the function from the stackframe. If the module can not
  retrieved, a `RuntimeError` is raised. '''

  if module is None:
    frame = sys._getframe(2) # get_calling_module() - rule - module
    if 'module' not in frame.f_globals:
      raise RuntimeError('could not read "module" variable')
    module = proxy.resolve_proxy(frame.f_globals['module'])
  else:
    module = proxy.resolve_proxy(module)

  if not isinstance(module, craftr.runtime.Module):
    raise RuntimeError('"module" is not a Module object')
  return module


class CommandBuilder(object):
  ''' This is a helper class to generate commands based on a set
  of options. These options can be passed to `__call__()` to generate
  the result list.

      builder = CommandBuilder(['clang++', '-c', '-arch', 'x86_amd64'])
      builder.switch('debug',
        enabled=['-g', '-O0'],
        disabled=['-O3'])
      build.add
      command = builder(debug=True)
  '''

  def __init__(self, base=()):
    super().__init__()
    self._parts = []
    self.append(base)

  def __call__(self, **options):
    ''' Generate the list using the specified *\*\*options*. '''

    result = []
    for part in self._parts:
      if part['type'] == 'append_args':
        result.extend(part['args'])
      elif part['type'] == 'append_func':
        args = part['func'](options)
        result.extend(lists.autoexpand(args))
      elif part['type'] == 'switch':
        value = options.get(part['name'], None)
        if part['func']:
          args = part['func'](value)
          result.extend(lists.autoexpand(args))
        if value:
          result.extend(part['enabled'])
        else:
          result.extend(part['disabled'])
      else:
        raise RuntimeError('invalid part type {!r}'.format(part['type']))
    return result

  def append(self, flags):
    ''' This function acts differently based on the type of *flags*. If
    it is a function, it will be called with a dictionary of all options
    as the first argument and the return value must be a list that will
    be appended to the result. Otherwise, *flags* is assumed to be a
    sequence that is directly appended to the result. All values are
    expanded using `lists.autoexpand()`. '''

    if callable(flags):
      self._parts.append({
        'type': 'append_func',
        'func': flags})
      return flags
    elif isinstance(flags, collections.Iterable):
      self._parts.append({
        'type': 'append_args',
        'args': lists.autoexpand(flags)})
    else:
      raise TypeError('flags must be callable or iterable')

  def switch(self, option, func=None, enabled=(), disabled=()):
    ''' If the option is enabled (ie. given and True), append the
    *enabled* items to the result, otherwise append *disabled*. If
    *func* is given, it is passed the values of *option* as the
    first argument.

    The *enabled* and *disabled* lists and the return value of
    *func* are expanded using the `lists.autoexpand()` function. '''

    if func and not callable(func):
      raise TypeError('func must be callable')
    self._parts.append({
      'type': 'switch',
      'name': option,
      'func': func,
      'enabled': lists.autoexpand(enabled),
      'disabled': lists.autoexpand(disabled)})


def build_archive(filename, base_dir, include=(), exclude=(), optional=(),
    prefix=None, quiet=False):
  ''' Build a ZIP archive at *filename* and include the specified files.
  The *base_dir* is stripped from the absolute filenames to find the
  arcname. '''

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
      craftr.logging.clear_line()
      print('writing {!r}... '.format(arcname), end='')
    zf.write(fn, arcname)
    if not quiet:
      print('done.', end='')
  zf.close()
  if not quiet:
    craftr.logging.clear_line()
    print('{} files compressed in {!r}'.format(len(files), filename))

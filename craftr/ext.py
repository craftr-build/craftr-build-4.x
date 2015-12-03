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

__all__ = ['CraftrImporter']

from craftr import magic, runtime, path

import craftr
import imp
import re
import sys
import warnings

# Mark this module as a package to be able to actually import sub
# modules from `craftr.ext`, otherwise the `CraftrImporter` is not
# even invoked at all.
__path__ = []


class CraftrImporter(object):
  ''' Meta-path import hook for importing Craftr modules from the
  `craftr.ext` parent namespace. Only functions inside a session
  context. '''

  def __init__(self):
    super().__init__()
    self._cache = {}

  def _get_module_ident(self, filename):
    ''' Extracts the module identifier from file at the specified
    *filename* and returns it, or None if the file does not contain
    a `craftr_module(...)` declaration in the first comment-block. '''

    expr = re.compile('#\s*craftr_module\((\w+)\)')
    with open(filename, "r") as fp:
      in_comment_block = False
      for line in map(str.rstrip, fp):
        if line.startswith('#'):
          in_comment_block = True
          match = expr.match(line)
          if match:
            return match.group(1)
        elif in_comment_block:
          return False

  def _check_file(self, filename):
    if not path.isfile(filename):
      return False
    ident = self._get_module_ident(filename)
    if not ident:
      message = 'no craftr_module() declaration in "{0}"'.format(filename)
      warnings.warn(message, ImportWarning)
      return False
    if ident in self._cache and self._cache[ident] != filename:
      message ='module "{0}" already found elsewhere'.format(ident)
      warnings.warn(message, ImportWarning)
      return False
    self._cache[ident] = filename
    return True

  def _rebuild_cache(self):
    ''' Rebuilds the importer cache for craftr modules. '''

    def check_dir(dirname):
      self._check_file(path.join(dirname, 'Craftfile'))
      for filename in path.listdir(dirname):
        if filename.endswith('.craftr'):
          self._check_file(filename)

    self._cache.clear()
    for dirname in map(path.normpath, sys.path):
      if not path.isdir(dirname):
        continue
      check_dir(dirname)
      # Also check second-level directories.
      for subdir in path.listdir(dirname):
        if path.isdir(subdir):
          check_dir(subdir)

  def _get_module_info(self, fullname):
    ''' Returns a tuple that contains information about a craftr module
    with the specified *fullname*. Either a namespace module or a real
    module can be loaded from this information.

    The return *type* is either `None`, `'namespace'` or `'module'`.
    The *filename* is only set when the *type* is `'module'`.

    Returns:
      tuple: `(type, filename)`
    '''

    self._rebuild_cache()  # xxx: do this only when syspath has changed!
    if fullname in self._cache:
      return ('module', self._cache[fullname])
    fullname += '.'
    for key in self._cache.keys():
      if key.startswith(fullname):
        return ('namespace', None)
    return (None, None)

  def find_module(self, fullname, path=None):
    if not fullname.startswith('craftr.ext.'):
      return None
    name = fullname[11:]
    if name in craftr.session.modules:
      # xxx: what if the existing module is a namespace module but we found a real one?
      return CraftrLoader(None, None)
    # xxx: take the *path* argument into account?
    kind, filename = self._get_module_info(name)
    if kind:
      return CraftrLoader(kind, filename)
    return None


class CraftrLoader(object):

  def __init__(self, kind, filename):
    super().__init__()
    self.kind = kind
    self.filename = filename

  def load_module(self, fullname):
    assert fullname.startswith('craftr.ext.')
    name = fullname[11:]
    if name in craftr.session.modules:
      sys.modules[fullname] = module = craftr.session.modules[name]
    else:
      assert self.kind and self.kind in ('namespace', 'module')
      module = imp.new_module(fullname)
      if self.kind == 'module':
        module.__file__ = self.filename
        runtime.init_module(module)
        with magic.enter_context(craftr.module, module):
          with open(self.filename, 'r') as fp:
            exec(compile(fp.read(), self.filename, 'exec'), vars(module))
      module.__path__ = []
      module.__session__ = magic.deref(craftr.session)
      craftr.session.modules[name] = module
      sys.modules[fullname] = module
    return module


def install():
  if not getattr(install, '_installed', False):
    sys.meta_path.append(CraftrImporter())
    install._installed = True

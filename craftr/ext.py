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

from craftr.globals import session
from craftr.magic import test_context, deref

import imp
import importlib
import sys

# Mark this module as a package to be able to actually import sub
# modules from `craftr.ext`, otherwise the `CraftrImporter` is not
# even invoked at all.
__path__ = []


class CraftrImporter(object):
  ''' Meta-path import hook for importing Craftr modules from the
  `craftr.ext` parent namespace. Only functions inside a session
  context. '''

  def find_module(self, fullname, path=None):
    if not fullname.startswith('craftr.ext.'):
      return None
    if not test_context(session):
      raise ImportError('can not import from craftr.ext outside the session context')
    name = fullname[11:]
    if name in session.modules:
      return self
    # xxx: find the module
    return self

  def load_module(self, fullname):
    assert test_context(session)
    assert fullname.startswith('craftr.ext.')
    name = fullname[11:]
    if name in session.modules:
      sys.modules[fullname] = module = session.modules[name]
    else:
      # xxx: load the module and initialize it.
      module = imp.new_module(fullname)
      sys.modules[fullname] = module
      session.modules[name] = module
      module.__path__ = []
      module.__session__ = deref(session)
    return module


sys.meta_path.append(CraftrImporter())

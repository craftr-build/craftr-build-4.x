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

__all__ = ['Session']

import sys
import craftr


class Session(object):
  ''' The `Session` object is the overseer for the process of loading
  and executing craftr modules. It manages the module loading process,
  a global configuration `Environment` and some global scope tasks such
  as resolving identifiers to concrete objects. '''

  def __init__(self):
    super().__init__()
    self.env = craftr.env.Environment()
    self.modules = {}

  def on_context_enter(self, prev):
    if prev is not None:
      raise RuntimeError('session context can not be nested')

  def on_context_leave(self):
    ''' Remove all `craftr.ext.` modules from `sys.modules` and make
    sure they're all in `Session.modules` (the modules are expected
    to be put there by the `craftr.ext.CraftrImporter`). '''

    for key, module in list(sys.modules.items()):
      if key.startswith('craftr.ext.'):
        name = key[11:]
        assert name in self.modules and self.modules[name] is module, key
        del sys.modules[key]
        try:
          # Remove the module from the `craftr.ext` modules contents, too.
          delattr(craftr.ext, name.split('.')[0])
        except AttributeError:
          pass


def init_module(module):
  ''' Called when a craftr module is being imported before it is
  executed to initialize its contents. '''

  module.project_dir = craftr.path.dirname(module.__file__)

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

from . import ident
from . import lists
from . import path
from . import proxy
from . import shell
import craftr
import sys


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

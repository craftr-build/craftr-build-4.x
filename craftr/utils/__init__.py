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

import sys
import dis
import craftr
import collections


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


def get_module_frame(module):
  ''' Returns the global scope (stack frame) at which *module* is being
  evaluated. This is usually used with `get_assigned_name()` to deduce
  the name of a target or pool declaration. '''

  # Find the frame that is executed for this module.
  frame = sys._getframe(1)
  while frame:
    if frame.f_locals is vars(module.locals):
      break
    frame = frame.f_back
  if not frame:
    raise RuntimeError('module frame could not be found')
  return frame


def get_assigned_name(frame):
  ''' Checks the bytecode of *frame* to find the name of the variable
  a result is being assigned to and returns that name. Returns the full
  left operand of the assignment. Raises a `ValueError` if the variable
  name could not be retrieved from the bytecode (eg. if an unpack sequence
  is on the left side of the assignment).

      >>> var = get_assigned_frame(sys._getframe())
      >>> assert var == 'var'
  '''

  SEARCHING, MATCHED = 1, 2
  state = SEARCHING
  result = ''
  for op in dis.get_instructions(frame.f_code):
    if state == SEARCHING and op.offset == frame.f_lasti:
      state = MATCHED
    elif state == MATCHED:
      if result:
        if op.opname == 'LOAD_ATTR':
          result += op.argval + '.'
        elif op.opname == 'STORE_ATTR':
          result += op.argval
          break
        else:
          raise ValueError('expected {LOAD_ATTR, STORE_ATTR}', op.opname)
      else:
        if op.opname in ('LOAD_NAME', 'LOAD_FAST'):
          result += op.argval + '.'
        elif op.opname in ('STORE_NAME', 'STORE_FAST'):
          result = op.argval
          break
        else:
          message = 'expected {LOAD_NAME, LOAD_FAST, STORE_NAME, STORE_FAST}'
          raise ValueError(message, op.opname)

  if not result:
    raise RuntimeError('last frame instruction not found')
  return result

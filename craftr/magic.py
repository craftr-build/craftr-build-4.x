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
''' This module is where all the magic comes from. '''

from contextlib import contextmanager
from sys import _getframe as get_frame

import dis
import werkzeug


class Proxy(werkzeug.LocalProxy):
  ''' This `werkzeug.LocalProxy` subclass returns the current object
  when called instead of forwarding the call to the current object. '''

  def __call__(self):
    return self._get_current_object()


def new_context(context_name):
  ''' Create a new context with the specified *context_name* and
  return a `Proxy` that represents the top-most object of the context
  stack. '''

  def _lookup():
    top = object.__getattribute__(proxy, '_proxy_localstack').top
    if top is None:
      raise RuntimeError('outside of {0!r} context'.format(context_name))
    return top

  proxy = Proxy(_lookup)
  stack = werkzeug.LocalStack()
  object.__setattr__(proxy, '_proxy_localstack', stack)
  return proxy


@contextmanager
def enter_context(context_proxy, context_obj):
  ''' Contextmanager that pushes the *context_obj* on the context stack
  of the specified *context_proxy* and pops it on exit. If the context
  object supports it, the methods `context_obj.on_context_enter()` and
  `context_obj.on_context_leave()` will be called. '''

  assert isinstance(context_proxy, Proxy)
  stack = object.__getattribute__(context_proxy, '_proxy_localstack')
  prev = stack.top
  stack.push(context_obj)
  try:
    if hasattr(context_obj, 'on_context_enter'):
      context_obj.on_context_enter(prev)
    yield
  finally:
    try:
      if hasattr(context_obj, 'on_context_leave'):
        context_obj.on_context_leave()
    finally:
      assert stack.pop() is context_obj


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


def get_module_frame(module):
  ''' Returns the stack frame that *module* is being executed in. If
  the stack frame can not be found, a `RuntimeError` is raised. '''

  frame = get_frame(1)
  while frame:
    if frame.f_globals is vars(module) and frame.f_locals is vars(module):
      return frame
    frame = frame.f_back
  raise RuntimeError('module frame can not be found')


def get_caller(stacklevel=1):
  ''' Returns the name of the calling function. '''

  return get_frame(stacklevel).f_code.co_name


def get_caller_human(stacklevel=1):
  ''' Returns the name of the calling function, concatenated with the
  craftr module name, if available. '''

  frame = get_frame(stacklevel)
  name = frame.f_code.co_name
  project_name = frame.f_globals.get('project_name')
  if project_name:
    if name == '<module>':
      name = project_name
    else:
      name = project_name + '.' + name + '()'
  return name

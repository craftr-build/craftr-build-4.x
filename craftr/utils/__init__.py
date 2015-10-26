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

from . import archive, ident, lists, path, proxy, shell

import sys
import dis
import craftr
import collections


class Translator(object):
  ''' The `Translator` is a base class for all classes that aim to
  implement building command-line arguments based on a set of options.
  Subclasses must implement methods that start with `_translate...()`
  that will be called for each key in the specified options dictionary.

  All `_translate...()` function will be invoked with all options. However,
  it usually makes sense to filter the options using function arguments
  and consume the rest with `**kwargs`. Example:

      def _translate_autodeps(self, autodeps=True, depfile='%%out.d', **kwargs):
        if autodeps and depfile:
          self.result.command += ['-MMD', '-MF', depfile]
          self.result.meta['depfile'] = depfile

  Only while the `_translate...()` functions are being called,
  `Translator.result` is set to a `Translator.Result` object. Handler
  methods are invoked sorted by name.

  > Note: Merging options works by the `merge_option()` method. By default,
  > lists and tuples are concatenated into a new list. This allows to, for
  > example, set a list of include directories on the instanc-level options
  > and have include directories passed to `translate()` be appended to it.

  Attributes:
    options (dict): A dictionary of options that will be merged with
      the options specified to `translate()`. Existing keys will simply
      be shadowed by the `translate()` options.
    result (Translator.Result): Only set inside the `translate()` call.
  '''

  class Result(object):
    __slots__ = ('program', 'command', 'meta', 'requires', 'options')
    def __init__(self, options):
      super().__init__()
      self.program = None
      self.command = []
      self.meta = {}
      self.requires = []
      self.options = options
    def __iter__(self):
      assert self.program is not None, 'translation result has no "program"'
      yield self.program
      yield from self.command

  def __init__(self, **options):
    super().__init__()
    self.options = options

  def __getitem__(self, key):
    return self.options[key]

  def __setitem__(self, key, value):
    self.options[key] = value

  def _pre_translate(self, prefix, options):
    pass

  def _validate(self, **options):
    pass

  def _translate(self, **options):
    pass

  def _post_translate(self, prefix, options):
    pass

  def translate(self, __prefix='', **options):
    ''' Calls the handler methods with the specified `**options`,
    merged with the instance-level options. If *__prefix* is specified,
    it will call only the handler methods that are followed by the
    *__prefix* after the `_translate` string.

    When the `Translator.options` are merged with the `**options`
    specified to this function, for each key `Translator.merge_option()`
    will be called. '''

    options = self.merge_options(self.options.copy(), options)
    self.result = Translator.Result(options)
    try:
      self._pre_translate(__prefix, options)
      if hasattr(self, '_pre_translate' + __prefix):
        getattr(self, '_pre_translate' + __prefix)(options)
      self._validate(**options)
      attrs = dir(self)
      attrs.sort()
      for key in attrs:
        if not key.startswith('_validate') or key == '_validate':
          continue
        if __prefix and not key[9:].startswith(__prefix):
          continue
        value = getattr(self, key)
        if callable(value):
          value(**options)
      self._translate(**options)
      for key in attrs:
        if not key.startswith('_translate') or key == '_translate':
          continue
        if __prefix and not key[10:].startswith(__prefix):
          continue
        value = getattr(self, key)
        if callable(value):
          value(**options)
      if not self.result.program:
        raise RuntimeError('translation result has no "program"')
      if hasattr(self, '_post_translate' + __prefix):
        getattr(self, '_post_translate' + __prefix)(options)
      self._post_translate(__prefix, options)
      return self.result
    finally:
      del self.result

  def merge_option(self, key, base, new):
    ''' This method is called for an option *key* that will override
    an existing entry with value *base* by the value *new*. The return
    value decides which value will be used.

    The default implementation returns *new* as-is, except if both *base*
    and *new* are tuples or lists, in which case both values are
    concatenated. '''

    if isinstance(base, (list, tuple)) and isinstance(new, (list, tuple)):
      return list(base) + list(new)
    return new

  def merge_options(self, base, new):
    ''' Merges the options of *new* onto *base*. '''

    for key, value in new.items():
      try:
        old = base[key]
      except KeyError:
        base[key] = value
      else:
        base[key] = self.merge_option(key, old, value)
    return base


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

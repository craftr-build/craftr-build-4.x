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

from . import lists
from . import path
from . import proxy
from . import shell
import re


class DataEntity(object):
  ''' Container for data of a module or a script. '''

  def __init__(self, entity_id):
    super().__init__()
    self.__entity_id__ = entity_id
    self.__entity_deps__ = []

  def __repr__(self):
    return '<DataEntity {0!r}>'.format(self.__entity_id__)

  def __getattr__(self, name):
    for dep in reversed(self.__entity_deps__):
      try:
        return getattr(dep, name)
      except AttributeError:
        pass
    raise AttributeError(name)


def singleton(x):
  ''' Decorator for a singleton class or function. The class or
  function will be called and the result returned. '''

  return x()


def validate_ident(ident):
  ''' Returns True if *ident* is a valid module or target identifier.
  Such an identifier can be like a Python variable but allowing
  namespace access by dots. '''

  if not re.match('^[A-z][A-z0-9\_\.]*$', ident):
    return False
  return not ident.endswith('.')


def validate_var(ident):
  ''' Returns True if *ident* is a valid variable name (without dots). '''

  return bool(re.match('^[A-z][A-z0-9\_\.]*$', ident))


def split_ident(ident):
  ''' Splits *ident* into module and variable name. '''

  if not validate_ident(ident):
    raise ValueError('invalid identifier', ident)
  parts = ident.split('.')
  return '.'.join(parts[:-1]), parts[-1]


def abs_ident(ident, parent):
  ''' If *ident* is a relative identifier (that is only a variable name),
  concatenates *ident* with *parent*. Returns *ident* otherwise. '''

  if not validate_ident(parent):
    raise ValueError('invalid identifier', parent)
  if not '.' in ident:
    if not validate_var(ident):
      raise ValueError('invalid variable name', ident)
    ident = parent + '.' + ident
  elif not validate_ident(ident):
    raise ValueError('invalid identifier', ident)

  return ident

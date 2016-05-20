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
''' Utility functions to read options from the environment. '''

__all__ = []

from craftr import module, environ


def get(name, default=None, inherit_global=True):
  ''' Reads an option value from the environment variables.
  The option name will be prefixed by the identifier of the
  module that is currently executed, eg:

  .. code:: python

    # craftr_module(test)
    from craftr import options, environ
    value = options.get('debug', inherit_global=False)
    # is equal to
    value = environ.get('test.debug')

  :param name: The name of the option.
  :param default: The default value that is returned if the
    option is not set in the environment.
  :param inherit_global: If this is True, the option is also
    searched globally (ie. *name* without the prefix of the
    currently executed module).
  '''

  full_name = module.project_name + '.' + name
  try:
    value = environ[full_name]
  except KeyError:
    if inherit_global:
      value = environ.get(name, default)
    else:
      value = default
  return value

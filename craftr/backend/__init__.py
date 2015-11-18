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

import importlib


def load_backend(backend_name):
  ''' Loads the module that implements the backend for the specified
  *backend_name*. First, it will attempt to import a module called
  `craftr_<x>_backend` and then `craftr.backend.<x>` where `<x>` is
  to be replaced with the actual backend name. '''

  if not isinstance(backend_name, str):
    raise TypeError('expected str, got {} instead'.format(type(backend_name).__name__))

  try:
    return importlib.import_module('craftr_{}_backend'.format(backend_name))
  except ImportError:
    pass
  try:
    return importlib.import_module('craftr.backend.' + backend_name)
  except ImportError:
    pass
  raise ValueError("no backend named '{}'".format(backend_name))

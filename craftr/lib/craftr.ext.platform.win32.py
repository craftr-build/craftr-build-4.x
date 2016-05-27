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

__all__ = ['name', 'standard', 'obj', 'bin', 'lib', 'dll', 'get_tool']

from craftr import path, environ
import functools

name = 'win'
standard = 'nt'

obj = lambda x: path.addsuffix(x, '.obj')
bin = lambda x: path.addsuffix(x, '.exe')
lib = lambda x: path.addsuffix(x, '.lib')
dll = lambda x: path.addsuffix(x, '.dll')


@functools.lru_cache(maxsize=None)
def get_tool(name):
  from craftr.ext.compiler import msvc
  # xxx: Implement detecting the compiler if no compiler toolset is
  # available in the PATH by default via VS__COMNTOOLS and even allow
  # using a GCC interface instead.
  if name == 'cc':
    return msvc.Compiler(environ.get('CC', 'cl'), 'c')
  elif name == 'cxx':
    return msvc.Compiler(environ.get('CXX', 'cl'), 'c++')
  elif name == 'asm':
    return msvc.Compiler(environ.get('AS', 'cl'), 'asm')
  elif name == 'ld':
    return msvc.Linker('link')
  elif name == 'ar':
    return msvc.Archiver('lib')
  else:
    raise ValueError(name)

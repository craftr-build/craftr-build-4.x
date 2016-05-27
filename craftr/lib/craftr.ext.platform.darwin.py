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

from craftr import environ, path
import craftr.ext.unix
import craftr.ext.compiler
import functools

name = 'mac'
standard = 'posix'

obj = lambda x: path.addsuffix(x, '.o')
bin = lambda x: x
lib = lambda x: path.addprefix(path.addsuffix(x, '.a'), 'lib')
dll = lambda x: path.addsuffix(x, '.dylib')


@functools.lru_cache(maxsize=None)
def get_tool(name):
  from craftr.ext.compiler import detect_compiler
  if name == 'cc':
    return detect_compiler(environ.get('CC', 'clang'), 'c')
  elif name == 'cxx':
    return detect_compiler(environ.get('CXX', 'clang++'), 'c++')
  elif name == 'asm':
    return detect_compiler(environ.get('AS', 'clang'), 'asm')
  elif name == 'ld':
    return detect_compiler(environ.get('CC', 'clang'), 'c')
  elif name ==  'ar':
    return craftr.ext.unix.Ar(environ.get('AR', 'ar'))
  else:
    raise ValueError(name)

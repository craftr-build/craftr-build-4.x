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

from craftr import path, environ, utils
from functools import lru_cache

name = 'win'
standard = 'nt'

obj = lambda x: path.addsuffix(x, '.obj')
bin = lambda x: path.addsuffix(x, '.exe')
lib = lambda x: path.addsuffix(x, '.lib')
dll = lambda x: path.addsuffix(x, '.dll')


@lru_cache()
def get_tool(name, __cache={}):
  from craftr.ext.compiler import msvc

  if 'suite' in __cache:
    # If we were detecting to use a Suite once, we will
    # use it always (damn this is so dirty).
    return getattr(__cache['suite'], name)

  # TODO: Support MinGW
  if name == 'cc' and ('CC' in environ or utils.test_program('cl')):
    return msvc.Compiler(environ.get('CC', 'cl'), 'c')
  elif name == 'cxx' and ('CXX' in environ or utils.test_program('cl')):
    return msvc.Compiler(environ.get('CXX', 'cl'), 'c++')
  elif name == 'asm' and ('AS' in environ or utils.test_program('cl')):
    return msvc.Compiler(environ.get('AS', 'cl'), 'asm')
  elif name == 'ld' and utils.test_program('cl'):
    return msvc.Linker('link', desc=get_tool('cc').desc)
  elif name == 'ar' and utils.test_program('cl'):
    return msvc.Archiver('lib')

  __cache['suite'] = msvc.MsvcSuite()
  return get_tool(name)

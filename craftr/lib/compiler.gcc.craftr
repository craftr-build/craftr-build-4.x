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

__all__ = ['GccCompiler']

from craftr import *
from .. import llvm
from functools import partial
import re


_e_gcc_version = r'^.*(gcc)\s+version\s+([\d\.\-]+).*\s*$'
_e_gcc_target = r'Target:\s*([\w\-\._]+)'
_e_gcc_thread = r'--enable-threads=([\w\-\._]+)'


@memoize_tool
def detect(program):
  ''' Assuming *program* points to GCC or GCC++, this function determines
  meta information about it. The returned dictionary contains the
  following keys:

  * version
  * version_str
  * name
  * target
  * thread_model
  * cpp_stdlib (only present for GCC++)

  :raise OSError: If *program* can not be executed (eg. if it does not exist).
  :raise ToolDetectionError: If *program* is not GCC or GCC++. '''

  output = shell.pipe([program, '-v']).output
  version = utils.gre_search(_e_gcc_version, output, re.I | re.M)
  target = utils.gre_search(_e_gcc_target, output, re.I)[1]
  thread_model = utils.gre_search(_e_gcc_thread, output, re.I)[1]

  if not all(version):
    raise ToolDetectionError('could not determine GCC version')

  result = {
    'version': version[2],
    'version_str': version[0].strip(),
    'name': version[1],
    'target': target,
    'thread_model': thread_model,
  }

  # Check for a C++ compiler.
  if program[-2:] == '++':
    stdlib = llvm.detect_cpp_stdlib(program)
    if stdlib:
      result['cpp_stdlib'] = stdlib
  return result


class GccCompiler(llvm.LlvmCompiler):
  ''' Interface for the GCC compiler.

  .. note:: Currently inherits the LLVM implementation. Will eventually
    get its own implementatio in the future, but not as long as the LLVM
    version works well for GCC, too.
  '''

  name = 'GCC (Craftr-LLVM-Backend)'

  def __init__(self, program, language='c', desc=None, **kwargs):
    if not desc:
      desc = detect(program)
    super().__init__(program=program, language=language, desc=desc, **kwargs)


Compiler = GccCompiler
Linker = partial(GccCompiler, language='c')

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

__all__ = ['FlexCompiler']

from craftr import *


class FlexCompiler(object):
  ''' Interface for the lex compiler. '''

  def __init__(self, program='flex'):
    super().__init__()
    self.program = program

  def compile(self, sources, output=None, debug=False, fast=False, case_insensitive=False,
      max_compatibility=False, performance_report=False, no_warn=False,
      interactive=False, bits=None, cpp=False, compress=None, prefix=None):

    compress_modes = {
      'align': 'a', 'equivalence': 'e', 'full': 'f', 'fast': 'F',
      'meta-equivalence': 'm', 'bypass': 'r'}

    if bits not in (None, 7, 8):
      raise ValueError('bits must be None, 7 or 8')
    if compress and not all(x in compress_modes for x in compress):
      raise ValueError('invalid compress flags')
    if not output:
      output = 'lex.yy.cc' if cpp else 'lex.yy.c'

    flags = ''
    if debug:
      flags += 'd'
    if fast:
      flags += 'f'
    if case_insensitive:
      flags += 'i'
    if max_compatibility:
      flags += 'l'
    if performance_report:
      flags += 'p'
    if no_warn:
      flags += 'w'
    if interactive:
      flags += 'I'
    if bits:
      flags += str(bits)
    if cpp:
      flags += '+'

    command = [self.program]
    if flags:
      command += ['-' + flags]
    if compress:
      command += '-C' + ''.join(compress_modes[x] for x in compress)
    if prefix:
      command += ['-P' + prefix]
    command += ['-o' + output]
    command += ['$in']

    return Target(command, expand_inputs(sources), [output])

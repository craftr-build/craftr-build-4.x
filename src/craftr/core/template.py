# -*- coding: utf8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2018  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This module implements the template compiler that is used to render commands
in an operator for every of its build sets.

Variables are referenced using `$varname` or `${varname}`. An input file set
is referenced using `$<setname` or ${<setname}` and an output file set with
`$@setname` or `${@setname}`.

A string that contains a file set reference is expanded for every element in
the file set. Multiple file set references in the same string are therefore
not allowed. The same is true (in combination) for variables that contain a
list of values, however that can only be determined at render time.
"""

import collections
import re

from nr.types.sumtype import Sumtype


class _Part(Sumtype):
  FileSet = Sumtype.Constructor('type', 'name')
  Var = Sumtype.Constructor('name')
  Str = Sumtype.Constructor('val')

  @Sumtype.MemberOf(FileSet)
  def to_str(self):
    return '${{{}{}}}'.format(self.type, self.name)

  @Sumtype.MemberOf(Var)
  def to_str(self):
    return '${{{}}}'.format(self.name)

  @Sumtype.MemberOf(Str)
  def to_str(self):
    return self.val


class _Template:

  def __init__(self, parts):
    self._parts = []
    for x in parts:
      if not isinstance(x, _Part):
        raise TypeError('expected _Part, got {}'.format(type(x).__name__))
      self._parts.append(x)

    # Multuple file set parts are not allowed in the same template.
    file_sets = [x for x in self._parts if x.is_file_set()]
    if len(file_sets) > 1:
      names = ', '.join([x.to_str() for x in file_sets])
      raise ValueError('multiple file references in the same string not '
                       'allowed, got [{}]'.format(names))
    self._has_file_set = len(file_sets) != 0

  def __str__(self):
    return ''.join(x.to_str() for x in self._parts)

  def __repr__(self):
    return '{}({!r})'.format(type(self).__name__, str(self))

  def __eq__(self, other):
    if isinstance(other, _Template):
      return self._parts == other._parts
    return False

  def file_sets(self):
    return [x for x in self._parts if x.is_file_set()]

  def vars(self):
    return [x for x in self._parts if x.is_var()]

  def render(self, inputs, outputs, variables, safe=False):
    prefix = ''
    expandable = None
    suffix = ''
    for x in self._parts:
      if x.is_var():
        if safe:
          value = variables.get(x.name, '')
        else:
          value = variables[x.name]
        is_seq = isinstance(value, collections.Sequence) and \
                 not isinstance(value, str)
        if is_seq and self._has_file_set:
          raise ValueError('variable {} can not be expanded as it contains '
                           'a sequence and this template already references '
                           'a file set. A template can not be expanded with '
                           'multiple variable-length elements.'.format(x.to_str()))
        if is_seq:
          assert expandable is None
          expandable = value
        else:
          if expandable is None: prefix += str(value)
          else: suffix += str(value)
      elif x.is_file_set():
        assert expandable is None
        source = inputs if x.type == '<' else outputs
        if safe:
          expandable = source.get(x.name, [])
        else:
          expandable = source[x.name]
      else:
        if expandable is None: prefix += str(x.val)
        else: suffix += str(x.val)
    if expandable is None:
      assert not suffix
      return [prefix]
    else:
      result = []
      for value in expandable:
        result.append(prefix + str(value) + suffix)
      return result

  def occurences(self, inputs, outputs, variables):
    for x in self._parts:
      if x.is_file_set():
        (inputs if x.type == '<' else outputs).add(x.name)
      elif x.is_var():
        variables.add(x.name)
    return inputs, outputs, variables


class TemplateCompiler:

  _regex = re.compile(r'\$([@<]?\w+)|\$\{([@<]?.*?)\}')

  def compile(self, arg: str):
    offset = 0
    parts = []
    while True:
      match = self._regex.search(arg, offset)
      if not match: break
      if offset < match.start():
        parts.append(_Part.Str(arg[offset:match.start()]))
      var = match.group(1) or match.group(2)
      if var[0] in '<@':
        parts.append(_Part.FileSet(var[0], var[1:]))
      else:
        parts.append(_Part.Var(var))
      offset = match.end()
    if offset < len(arg):
      parts.append(_Part.Str(arg[offset:]))
    return _Template(parts)

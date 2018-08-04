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
This module contains classes to represent all information in the build graph.
The build graph consists of three major elements: Targets, Operators and
Buildsets.

Operators are basically system commands with placeholders for files and
variables. These placeholders are filled by information that is specified
in the Buildsets.

Targets contain properties from which the Operators and Buildsets are
generated. The public properties of targets can be inherited by another target
via inclusion.
"""

__all__ = ['BuildSet', 'Operator', 'Target', 'DiskInterface']

import nr.fs
import re

from nr.types.set import OrderedSet
from typing import List, Optional


class Behaviour:
  """
  This interface implements some methods that influence the behaviour of the
  build graph components. The default implementation is usually sufficient.
  """

  def canonicalize_path(self, path):
    """
    Canonicalize the specified *path*, turning it absolute and reducing it
    to the most relevant and normalized form. The default implementation
    acts as an alias to #nr.fs.canonical().
    """

    return nr.fs.canonical(path)

  def expand_placeholders(self, commands: List[List[str]],
                          build_set: 'BuildSet'):
    """
    Substitutes the placeholders in the list of *commands* with the variables
    and files in the specified build set.

    The default implementation replaces variables in the following format:

    - Variables: `$var`, `${var}`
    - Input files: `$<var`, `${<var}`
    - Output files: `$@var`, `${@var}`

    Arguments that have a prefix and/or suffix around a input/output file set
    placeholder are expanded so that the strings are preserved around every
    element in the set.

    Currently only a single placeholder per argument is supported.
    """

    regex = re.compile(r'\$([@<]?\w+)|\$\{([@<].*?)\}')
    result = []
    for command in commands:
      result.append([])
      for arg in command:
        match = regex.search(arg)
        if not match:
          result[-1].append(arg)
          continue

        prefix = arg[:match.start()]
        suffix = arg[match.end():]
        var = match.group(1) or match.group(2)

        if var[0] == '<':
          value = build_set.get_input_file_set(var[1:])
        elif var[0] == '@':
          value = build_set.get_file_set(var[1:])
        else:
          value = build_set.get_variable(var)

        if isinstance(value, (list, tuple, set, OrderedSet)):
          for x in value:
            result[-1].append(prefix + x + suffix)
        else:
          result[-1].append(prefix + str(value) + suffix)

    return result


class BuildSet:
  """
  A build set is a collection of named sets that contain absolute filenames,
  as well as a collection of variables and a list of dependent build sets.

  Build sets may be attached to an #Operator in which case they represent the
  files produced by the commands specified in the operator. In any other case,
  the build set represents a list of either already existing files (pure
  inputs) or a subset of the files of its inputs.
  """

  def __init__(self, master: 'Master',
               inputs: List['BuildSet'],
               operator: Optional['Operator']):

    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    self._master = master

    self._inputs = []
    for x in inputs:
      if not isinstance(x, BuildSet):
        raise TypeError('expected BuildSet, got {}'.format(type(x).__name__))
      if x not in self._inputs:
        self._inputs.append(x)

    if operator is not None and not isinstance(operator, Operator):
      raise TypeError('expected Operator, got {}'
        .format(type(operator).__name__))
    self._operator = operator

    self._files = {}
    self._vars = {}

  def __repr__(self):
    return '<{} len(inputs)={} operator={}>'.format(
      type(self).__name__, len(self._inputs), self._operator)

  @property
  def master(self):
    return self._master

  @property
  def inputs(self):
    return self._inputs[:]

  @property
  def operator(self):
    return self._operator

  @property
  def file_sets(self):
    """
    Returns a set of the file set names.
    """

    return set(self._files.keys())

  def get_file_set(self, set_name):
    """
    Return a copy of the file set with the name *set_name*. If the set does
    not exist in the operator, an empty set is returned instead.
    """

    try:
      return OrderedSet(self._files[set_name])
    except KeyError:
      return OrderedSet()

  def get_input_file_set(self, set_name):
    """
    Returns a concatenated file set from the inputs of this build set.
    """

    result = OrderedSet()
    for x in self._inputs:
      result |= x.get_file_set(set_name)
    return result

  def add_files(self, set_name, files):
    """
    Add a number of *files* to the set with the name *set_name*. All files
    added to a set in the file operator are canonicalized using the
    #Behaviour.canonicalize_path() method.
    """

    file_set = self._files.setdefault(set_name, OrderedSet())
    for file in files:
      file_set.add(self._master.behaviour.canonicalize_path(file))

  def remove(self):
    """
    Removes the build set from the operator.
    """

    if not self._operator:
      return

    self._operator._build_sets.remove(self)
    self._operator = None


class Operator:
  """
  An operator defines one or more system commands that is executed to produce
  output files from input files. These files are declared in a #BuildSet that
  must be attached to the operator.

  Every operator must be attached to a #Target.
  """

  def __init__(self, name: str,
               master: Behaviour,
               target: 'Target',
               commands: List[List[str]]):

    if not isinstance(name, str):
      raise TypeError('expected str, got {}'.format(type(name).__name__))
    if not name:
      raise ValueError('name must not be empty')
    self._name = name

    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    self._master = master

    if not isinstance(target, Target):
      raise TypeError('expected Target, got {}'.format(type(target).__name__))
    self._target = target

    if not isinstance(commands, list):
      raise TypeError('expected list, got {}'.format(type(commands).__name__))
    for x in commands:
      if not isinstance(x, list):
        raise TypeError('expected list, got {}'.format(type(x).__name__))
      for y in x:
        if not isinstance(y, str):
          raise TypeError('expected str, got {}'.format(type(y).__name__))
    self._commands = commands

    self._build_sets = []

  @property
  def name(self):
    return self._name

  @property
  def master(self):
    return self._master

  @property
  def target(self):
    return self._target

  @property
  def commands(self):
    return [x[:] for x in self._commands]

  @property
  def build_sets(self):
    return self._build_sets[:]

  def add_build_set(self, build_set):
    if build_set._operator is not self:
      raise ValueError('add_build_set(): BuildSet.operator must be self')
    if build_set in self._build_sets:
      raise RuntimeError('add_build_set(): BuildSet is already added')
    self._build_sets.append(build_set)
    return build_set

  def expand_placeholders(self, build_set, strict=True):
    """
    A shortcut for #Behaviour.expand_placeholders().
    """

    if strict and (
        build_set._operator is not self or
        build_set not in self._build_sets):
      raise RuntimeError('(strict=True) BuildSet is not related to this operator')
    return self._master.behaviour.expand_placeholders(self._commands, build_set)


class Target:
  """
  A target contains private and public properties that will then be turned
  into operators which are also stored inside the target.
  """

  def __init__(self, name: str, master: 'Master'):
    if not isinstance(name, str):
      raise TypeError('expected str, got {}'.format(type(name).__name__))
    if not name:
      raise ValueError('name must not be empty')
    self._name = name

    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    self._master = master

    self._operators = {}

  @property
  def name(self):
    return self._name

  @property
  def master(self):
    return self._master

  @property
  def operators(self):
    return self._operators.values()

  def add_operator(self, operator):
    if not isinstance(operator, Operator):
      raise TypeError('expected Operator, got {}'.format(
        type(operator).__name__))
    if operator._name in self._operators:
      raise TypeError('Operator name {!r} already occupied in Target {!r}'
        .format(operator._name, self._name))
    self._operators[operator._name] = operator
    return operator


class Master:
  """
  This class keeps track of targets and provides the #Behaviour for the build.
  """

  def __init__(self, behaviour: Behaviour = Behaviour()):
    if not isinstance(behaviour, Behaviour):
      raise TypeError('expected Behaviour, got {}'.format(
        type(behaviour).__name__))
    self._behaviour = behaviour

    self._targets = {}

  @property
  def behaviour(self):
    return self._behaviour

  @property
  def targets(self):
    return self._targets.values()

  def add_target(self, target):
    if not isinstance(target, Target):
      raise TypeError('expected Target, got {}'.format(type(target).__name__))
    if target._name in self._targets:
      raise ValueError('Target name {!r} already occupied'.format(target._name))
    self._targets[target._name] = target
    return target


def dump_dotviz(obj, root=True, fp=None, seen=None):
  if seen is None:
    seen = set()
  import builtins
  print = lambda *a: builtins.print(*a, file=fp)
  if root:
    print('digraph {')
  if isinstance(obj, Master):
    key = 'MASTER'
    for target in obj.targets:
      target_key = dump_dotviz(target, False, fp, seen)
      print('  "{}" -> "{}";'.format(target_key, key))
  elif isinstance(obj, Target):
    key = 'Target:{}'.format(obj.name)
    for operator in obj.operators:
      op_key = dump_dotviz(operator, False, fp, seen)
      print('  "{}" -> "{}";'.format(op_key, key))
  elif isinstance(obj, Operator):
    key = 'Operator:{}'.format(obj.name)
    for build_set in obj.build_sets:
      set_key = dump_dotviz(build_set, False, fp, seen)
      print('  "{}" -> "{}";'.format(set_key, key))
  elif isinstance(obj, BuildSet):
    key = 'BuildSet:{}'.format(id(obj))
    if obj not in seen:
      seen.add(obj)
      for build_set in obj.inputs:
        set_key = dump_dotviz(build_set, False, fp, seen)
        print('  "{}" -> "{}";'.format(set_key, key))
  else:
    raise TypeError(type(obj))
  print('  "{}";'.format(key))
  if root:
    print('}')
  return key

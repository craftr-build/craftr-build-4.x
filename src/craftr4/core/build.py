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

__all__ = ['Behaviour', 'BuildSet', 'Operator', 'Target', 'Master']

import nr.fs
import re

from nr.types.set import OrderedSet
from typing import List, Optional, Union


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

  def substitute(self, arg: str, build_set: 'BuildSet', single: bool = True):
    """
    Subsitute a placeholder in the string *arg*.

    TODO: Support multiple placeholders in the string.

    The default implementation replaces variables in the following format:

    - Variables: `$var`, `${var}`
    - Input files: `$<var`, `${<var}`
    - Output files: `$@var`, `${@var}`

    Arguments that have a prefix and/or suffix around a input/output file set
    placeholder are expanded so that the strings are preserved around every
    element in the set.

    Currently only a single placeholder per argument is supported.
    """

    import shlex
    regex = re.compile(r'\$([@<]?\w+)|\$\{([@<].*?)\}')

    if single:
      return ' '.join(self.multi_substitute(shlex.split(arg), build_set))

    result = []
    match = regex.search(arg)
    if not match:
      result.append(arg)
      return result

    prefix = arg[:match.start()]
    suffix = arg[match.end():]
    var = match.group(1) or match.group(2)

    if var[0] == '<':
      value = build_set.get_input_file_set(var[1:])
    elif var[0] == '@':
      value = build_set.get_file_set(var[1:])
    else:
      value = build_set.variables[var]

    if isinstance(value, (list, tuple, set, OrderedSet)):
      for x in value:
        result.append(prefix + x + suffix)
    else:
      result.append(prefix + str(value) + suffix)

    return result

  def multi_substitute(self, arg: List, build_set: 'BuildSet'):
    result = []
    for x in arg:
      if isinstance(x, str):
        result += self.substitute(x, build_set, False)
      else:
        result.append(self.multi_substitute(x, build_set))
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
               description: Optional[str] = None):

    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    self._master = master

    self._inputs = []
    for x in inputs:
      if not isinstance(x, BuildSet):
        raise TypeError('expected BuildSet, got {}'.format(type(x).__name__))
      if x not in self._inputs:
        self._inputs.append(x)

    if description is not None and not isinstance(description, str):
      raise TypeError('expected str, got {}'.format(
        type(description).__name__))
    self._description = description

    self._operator = None
    self._files = {}
    self._vars = {}

  def __repr__(self):
    return '<{} file_sets={} operator={}>'.format(
      type(self).__name__, self.file_sets, self._operator)

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

  @property
  def variables(self):
    return self._vars

  @property
  def description(self):
    return self._description

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

  def get_commands(self):
    """
    Return the expanded commands for the build set from the operator.
    This method raises a #RuntimeError if the build set is not attached
    to an operator.
    """

    if not self._operator:
      raise TypeError('build set is not attached to an operator')
    return self._master.behaviour.multi_substitute(self._operator._commands, self)

  def get_description(self):
    """
    Return the description of the build set with variables expanded.
    """

    if not self._operator:
      return self._description
    return self._master.behaviour.substitute(self._description, self)


class Operator:
  """
  An operator defines one or more system commands that is executed to produce
  output files from input files. These files are declared in a #BuildSet that
  must be attached to the operator.

  Every operator must be attached to a #Target.
  """

  def __init__(self, name: str,
               master: Behaviour,
               commands: List[List[str]]):

    if not isinstance(name, str):
      raise TypeError('expected str, got {}'.format(type(name).__name__))
    if not name:
      raise ValueError('name must not be empty')
    self._name = name

    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    self._master = master

    if not isinstance(commands, list):
      raise TypeError('expected list, got {}'.format(type(commands).__name__))
    for x in commands:
      if not isinstance(x, list):
        raise TypeError('expected list, got {}'.format(type(x).__name__))
      for y in x:
        if not isinstance(y, str):
          raise TypeError('expected str, got {}'.format(type(y).__name__))
    self._commands = commands

    self._target = None
    self._build_sets = []

  def __repr__(self):
    return '<Operator name={!r} target={!r}>'.format(
      self._name, self._target._name)

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
    if build_set._operator is None:
      build_set._operator = self
    if build_set._operator is not self:
      raise ValueError('add_build_set(): BuildSet belongs to another Operator')
    if build_set in self._build_sets:
      raise RuntimeError('add_build_set(): BuildSet is already added')
    self._build_sets.append(build_set)
    return build_set


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

  def __repr__(self):
    return '<Target name={!r}>'.format(self._name)

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
    if operator._target is None:
      operator._target = self
    if operator._target is not self:
      raise RuntimeError('add_operator(): Operator belongs to another target')
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


def dump_dotviz(obj, root=True, fp=None):
  import builtins
  import shlex
  import sys

  def print(*args):
    frame = sys._getframe(1)
    while 'indent' not in frame.f_locals:
      frame = frame.f_back
    indent = frame.f_locals['indent']
    builtins.print('  ' * indent + ' '.join(map(str, args)), file=fp)

  seen = set()

  indent = 0
  print('digraph {')
  indent = 1
  print('graph [fontsize=10 fontname="monospace"];')
  print('node [shape=record fontsize=10 fontname="monospace"];')

  def node(node_id, **attrs):
    attrs = ' '.join(attr(k, v, False) for k, v in attrs.items())
    print('"{}" [{}];'.format(node_id, attrs))

  def edge(src_id, dst_id, **attrs):
    attrs = ' '.join(attr(k, v, False) for k, v in attrs.items())
    print('"{}" -> "{}" [{}];'.format(src_id, dst_id, attrs))

  def attr(key, value, semicolon=True):
    value = str(value)
    value = value.replace('"', '\\"').replace('{', '\\{').replace('}', '\\}')
    value = value.replace('\n', '\\n')
    res = '{}="{}"'.format(key, value)
    if semicolon:
      res += ';'
    return res

  def target_key(target):
    return 'Target:{}'.format(target.name)

  def operator_key(op):
    return 'Operator:{}/{}'.format(op.target.name, op.name)

  def build_set_key(bset):
    return id(bset)

  def handle_master(master, indent):
    [handle_target(x, indent) for x in master.targets]

  def handle_target(target, indent):
    key = target_key(target)
    print('subgraph "cluster_{}" {{'.format(key))
    indent += 1
    print(attr('label', 'Target: {}'.format(target.name)))
    print(attr('color', 'seagreen3'))
    print(attr('fillcolor', 'seagreen1'))
    print(attr('style', 'filled'))
    [handle_operator(x, indent) for x in target.operators]
    indent -= 1
    print('}')

  def handle_operator(op, indent):
    key = operator_key(op)
    print('subgraph "cluster_{}" {{'.format(key))
    indent += 1
    print(attr('label', 'Operator: {}'.format(op.name)))
    print(attr('color', 'skyblue4'))
    print(attr('fillcolor', 'skyblue'))
    print(attr('style', 'filled'))
    lines = []
    for cmd in op.commands:
      lines.append(' '.join(shlex.quote(x) for x in cmd))
    attrs = {'label': '\n'.join(lines), 'shape': 'rectangle',
             'color': 'skyblue4', 'fillcolor': 'skyblue4',
             'style': 'filled,rounded'}
    node(key, **attrs)
    for bset in op.build_sets:
      #edge(key, build_set_key(bset), style='dashed', color='darkorange')
      handle_build_set(bset, indent)
    print('{')
    indent += 1
    print(attr('rank', 'same'))
    node(key, group=key)
    for bset in op.build_sets:
      node(build_set_key(bset), group=key)
    indent -= 1
    print('}')
    indent -= 1
    print('}')

  def handle_build_set(bset, indent):
    if bset in seen:
      return
    seen.add(bset)
    key = build_set_key(bset)
    lines = []
    for set_name in bset.file_sets:
      lines.append('{} = {}'.format(set_name, [nr.fs.base(x) for x in bset.get_file_set(set_name)]))
    for k, v in bset.variables.items():
      lines.append('{} = {!r}'.format(k, v))
    attrs = {'label': '\n'.join(lines), 'style': 'filled'}
    if not bset.operator and bset.inputs:
      attrs['color'] = 'gray72'
      attrs['fillcolor'] = 'gray86'
    elif not bset.operator:
      attrs['color'] = 'orange4'
      attrs['fillcolor'] = 'orange2'
    else:
      attrs['color'] = 'slateblue3'
      attrs['fillcolor'] = 'slateblue1'
    node(key, **attrs)
    for other in bset.inputs:
      handle_build_set(other, indent)
      edge(build_set_key(other), key)

  if isinstance(obj, Master):
    handle_master(obj, indent)
  elif isinstance(obj, Target):
    handle_target(obj, indent)
  elif isinstance(obj, Operator):
    handle_operator(obj, indent)
  elif isinstance(obj, BuildSet):
    handle_build_set(obj, indent)
  else:
    raise TypeError(type(obj))

  indent -= 1
  print('}')


def topo_sort(master):
  """
  Topologically sort all build sets in the build graph contained in the
  #Master node. Returns a generator yielding #BuildSet objects in order.
  """

  # A mirror of the inputs for every build set, allowing us to remove
  # edge for this algorithm without actually modifying the graph.
  bset_inputs = {}

  # A dictionary that reverses the dependencies between build sets.
  bset_reverse = {}

  # A set of build sets that have no input.
  bset_start = set()

  for target in master.targets:
    for op in target.operators:
      queue = list(op.build_sets)
      while queue:
        bset = queue.pop()
        if bset in bset_inputs:
          continue
        bset_inputs[bset] = list(bset.inputs)
        bset_reverse.setdefault(bset, set())
        for x in bset.inputs:
          bset_reverse.setdefault(x, set()).add(bset)
        if not bset.inputs:
          bset_start.add(bset)
        queue += bset.inputs

  while bset_start:
    bset = bset_start.pop()
    yield bset
    for x in bset_reverse[bset]:
      bset_inputs[x].remove(bset)
      if not bset_inputs[x]:
        bset_start.add(x)
    bset_reverse[bset] = set()


def execute(master):
  """
  Executes the full build graph -- useful for development tests.
  """

  import shlex
  import subprocess

  for build_set in topo_sort(master):
    if not build_set.operator:
      continue
    prefix = '[{}/{}]'.format(build_set.operator.target.name, build_set.operator.name)
    if build_set.description:
      print(prefix, build_set.get_description())
    else:
      print(prefix)
    commands = build_set.get_commands()
    for cmd in commands:
      print('  $', ' '.join(shlex.quote(x) for x in cmd))
      subprocess.check_call(cmd)

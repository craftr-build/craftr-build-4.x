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

import io
import nr.fs
import re
import shlex

from nr.types.set import OrderedSet
from typing import Dict, List, Optional, Union


class Substitutor:
  """
  This class implements substition of files and variables with data from
  a #BuildSet.
  """

  _regex = re.compile(r'\$([@<]?\w+)|\$\{([@<].*?)\}')

  def subst(self, arg: str, build_set: 'BuildSet', single: bool = False):
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

    if not single:
      return ' '.join(self.multi_substitute(shlex.split(arg), build_set))

    result = []
    match = self._regex.search(arg)
    if not match:
      result.append(arg)
      return result

    prefix = arg[:match.start()]
    suffix = arg[match.end():]
    var = match.group(1) or match.group(2)

    if var[0] == '<':
      value = build_set.inputs[var[1:]]
    elif var[0] == '@':
      value = build_set.outputs[var[1:]]
    else:
      if var in build_set.variables:
        value = build_set.variables[var]
      else:
        value = build_set.operator.variables[var]

    if isinstance(value, (list, tuple, set, OrderedSet, FileSet)):
      for x in value:
        result.append(prefix + x + suffix)
    else:
      result.append(prefix + str(value) + suffix)

    return result

  def multi_subst(self, arg: List, build_set: 'BuildSet'):
    result = []
    for x in arg:
      if isinstance(x, str):
        result += self.subst(x, build_set, True)
      else:
        result.append(self.multi_subst(x, build_set))
    return result

  def occurences(self, arg: str, single: bool = False):
    if not single:
      return ' '.join(self.multi_occurences(shlex.split(arg)))

    match = self._regex.search(arg)
    if not match:
      return [], [], []
    var = match.group(1) or match.group(2)
    if var[0] == '@':
      return [], [var[1:]], []
    elif var[0] == '<':
      return [var[1:]], [], []
    else:
      return [], [], [var]

  def multi_occurences(self, arg: List):
    in_files, out_files, vars = set(), set(), set()
    for x in arg:
      if isinstance(x, str):
        r = self.occurences(x, True)
      else:
        r = self.multi_occurences(x)
      in_files.update(r[0])
      out_files.update(r[1])
      vars.update(r[2])
    return in_files, out_files, vars


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

  def get_substitutor(self):
    return Substitutor()


class FileSet:
  """
  Represents an ordered set of files. File sets are combined to create a
  #BuildSet that, together with an #Operator, form a single build action.
  Files in the set are stored only in canonical form using
  #Behaviour.canonicalize_path().

  Linking file sets is not mandatory but highly recommended for debugging
  purposes.

  Adding a #FileSet to a #BuildSet will establish links in the #build_sets_in
  and #build_sets_out.
  """

  def __init__(self, master: 'Master',
               files: List[str] = None,
               inputs: List['FileSet'] = None):

    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    self._master = master

    if inputs is None:
      inputs = []
    self._inputs = OrderedSet()
    if not isinstance(inputs, list):
      raise TypeError('expected list, got {}'.format(type(inputs).__name__))
    for x in inputs:
      if not isinstance(x, FileSet):
        raise TypeError('expected FileSet, got {}'.format(type(x).__name__))
      self._inputs.add(x)

    self._files = OrderedSet()
    self.add_files(files or [])

    self._build_sets_in = {}
    self._build_sets_out = {}

  def __repr__(self):
    return '{}({{{}}})'.format(
      type(self).__name__, ', '.join(repr(x) for x in self._files))

  def __len__(self):
    return len(self._files)

  def __getitem__(self, index):
    return self._files[index]

  def __iter__(self):
    return iter(self._files)

  @property
  def inputs(self):
    return self._inputs

  @property
  def aliases(self):
    return set(self._build_sets_in.values()) | set(self._build_sets_out.values())

  def add_file(self, filename: str):
    self._files.add(self._master.behaviour.canonicalize_path(filename))

  def add_files(self, files: List[str]):
    canonical = self._master.behaviour.canonicalize_path
    self._files.update(canonical(x) for x in files)

  def add_from(self, file_set: 'FileSet'):
    self._inputs.add(file_set)
    self._files.update(file_set._files)

  def clear(self):
    self._files.clear()

  def fill_for(self, ref_set: 'FileSet', update: callable):
    while len(self) < len(ref_set):
      self.add_file(update(ref_set[len(self)]))


class BuildSet:
  """
  A build set is a collection of named #FileSet objects in either an input
  or output slot.

  Build sets may be attached to an #Operator in which case they represent the
  files produced by the commands specified in the operator. In any other case,
  the build set represents a list of either already existing files (pure
  inputs) or a subset of the files of its inputs.
  """

  def __init__(self, master: 'Master',
               alias: str = None,
               description: Optional[str] = None,
               inputs: Dict[str, FileSet] = None,
               outputs: Dict[str, FileSet] = None,
               variables: Dict[str, object] = None):

    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    self._master = master

    self._inputs = {}
    for key, value in (inputs or {}).items():
      if not isinstance(value, FileSet):
        raise TypeError('expected FileSet, got {}'.format(type(value).__name__))
      self._inputs[key] = value
      value._build_sets_in[self] = key

    self._outputs = {}
    for key, value in (outputs or {}).items():
      if not isinstance(value, FileSet):
        raise TypeError('expected FileSet, got {}'.format(type(value).__name__))
      self._outputs[key] = value
      value._build_sets_out[self] = key

    if variables is not None and not isinstance(variables, dict):
      raise TypeError('expected dict, got {}'.format(type(variables).__name__))
    self._variables = dict(variables or {})

    if alias is not None and not isinstance(alias, str):
      raise TypeError('expected str, got {}'.format(type(alias).__name__))
    self._alias = alias

    if description is not None and not isinstance(description, str):
      raise TypeError('expected str, got {}'.format(
        type(description).__name__))
    self._description = description

    self._operator = None

  def __repr__(self):
    return '<{} operator={} inputs={} outputs={} variables={}>'.format(
      type(self).__name__, self.operator, set(self._inputs.keys()),
      set(self._outputs.keys()), set(self._variables.keys()))

  def __contains__(self, set_name):
    return set_name in self._files

  def __getitem__(self, set_name):
    return list(self._files[set_name])

  @property
  def master(self):
    return self._master

  @property
  def inputs(self):
    return self._inputs

  @property
  def outputs(self):
    return self._outputs

  @property
  def variables(self):
    return self._variables

  @property
  def alias(self):
    return self._alias

  @property
  def description(self):
    return self._description

  @property
  def operator(self):
    return self._operator

  def get_commands(self):
    """
    Return the expanded commands for the build set from the operator.
    This method raises a #RuntimeError if the build set is not attached
    to an operator.
    """

    if not self._operator:
      raise TypeError('build set is not attached to an operator')
    subst = self._master.behaviour.get_substitutor()
    return subst.multi_subst(self._operator._commands, self)

  def get_description(self):
    """
    Return the description of the build set with variables expanded.
    """

    if not self._operator:
      return self._description
    subst = self._master.behaviour.get_substitutor()
    return subst.subst(self._description, self)

  def fizzle(self):
    """
    Fizzle any connection, removing the build set from any operator that
    it is attached to as well as removing the links between itself and its
    file sets.
    """

    if self._operator:
      self._operator._build_sets.remove(self)
      self._operator = None
    for fset in self._inputs.values():
      fset._build_sets_in.pop(self)
    for fset in self._outputs.values():
      fset._build_sets_out.pop(self)


class Operator:
  """
  An operator defines one or more system commands that is executed to produce
  output files from input files. These files are declared in a #BuildSet that
  must be attached to the operator.

  Every operator must be attached to a #Target.
  """

  def __init__(self, name: str,
               master: 'Master',
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
    self._input_filesets, self._output_filesets, self._varnames = \
        master.behaviour.get_substitutor().multi_occurences(commands)

    self._target = None
    self._build_sets = []
    self._vars = {}

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
  def variables(self):
    return self._vars

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
    for set_name in self._input_filesets:
      if set_name not in build_set.inputs:
        raise RuntimeError('operator requires ${{<{}}} which is not '
                           'provided by this build set'.format(set_name))
    for set_name in self._output_filesets:
      if set_name not in build_set.outputs:
        raise RuntimeError('operator requires ${{@{}}} which is not '
                           'provided by this build set'.format(set_name))
    for var_name in self._varnames:
      if var_name not in self._vars and var_name not in build_set._vars:
        raise RuntimeError('operator requires ${{{}}} which is not provided '
                           'by this build set'.format(var_name))
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

  def get_operator(self, name):
    return self._operators[name]


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

  def get_target(self, name):
    return self._targets[name]


class GraphvizExporter:

  def __init__(self, fp):
    self._indent = 0
    self._fp = fp
    self._seen = set()

  def node(self, node_id, **attrs):
    if 'BuildSet' in node_id: import pdb; pdb.set_trace()
    attrs = ' '.join(self.attr(k, v, False) for k, v in attrs.items())
    return '"{}" [{}];'.format(node_id, attrs)

  def edge(self, src_id, dst_id, **attrs):
    attrs = ' '.join(self.attr(k, v, False) for k, v in attrs.items())
    return '"{}" -> "{}" [{}];'.format(src_id, dst_id, attrs)

  def attr(self, key, value, semicolon=True):
    value = str(value)
    value = value.replace('"', '\\"').replace('{', '\\{').replace('}', '\\}')
    value = value.replace('\n', '\\n')
    res = '{}="{}"'.format(key, value)
    if semicolon:
      res += ';'
    return res

  def key_of(self, obj):
    if isinstance(obj, Target):
      return '{}'.format(obj.name)
    elif isinstance(obj, Operator):
      return '{}/{}'.format(obj.target.name, obj.name)
    elif isinstance(obj, FileSet):
      return 'FileSet:{}'.format(id(obj))
    elif isinstance(obj, BuildSet):
      return 'BuildSet:{}'.format(id(obj))
    else:
      raise TypeError(type(obj))

  def print(self, *args):
    print('  ' * self._indent + '  '.join(map(str, args)), file=self._fp)

  def preamble(self):
    self.print('digraph {')
    self._indent += 1
    self.print('graph [fontsize=10 fontname="monospace"];')
    self.print('node [shape=record fontsize=10 fontname="monospace" style="filled"];')

  def epilogue(self):
    self._indent -= 1
    self.print('}')

  def handle_master(self, master):
    [self.handle_target(x) for x in master.targets]

  def handle_target(self, target):
    key = self.key_of(target)
    self.print('subgraph "cluster_{}" {{'.format(key))
    self._indent += 1
    self.print(self.attr('label', 'Target: {}'.format(target.name)))
    self.print(self.attr('labeljust', 'l'))
    self.print(self.attr('color', 'seagreen3'))
    self.print(self.attr('fillcolor', 'seagreen1'))
    self.print(self.attr('style', 'filled'))
    [self.handle_operator(x) for x in target.operators]
    self._indent -= 1
    self.print('}')

  def handle_operator(self, op):
    key = self.key_of(op)
    self.print('subgraph "cluster_{}" {{'.format(key))
    self._indent += 1
    self.print(self.attr('label', 'Operator: {}'.format(op.name)))
    self.print(self.attr('labeljust', 'l'))
    self.print(self.attr('color', 'skyblue4'))
    self.print(self.attr('fillcolor', 'skyblue'))
    self.print(self.attr('style', 'filled'))
    lines = []
    for cmd in op.commands:
      lines.append(' '.join(shlex.quote(x) for x in cmd))
    attrs = {'label': '\n'.join(lines), 'shape': 'rectangle',
             'color': 'brown4', 'fillcolor': 'brown2',
             'style': 'filled,rounded'}
    self.print(self.node(key, **attrs))
    for bset in op.build_sets:
      #edge(key, build_set_key(bset), style='dashed', color='darkorange')
      self.handle_build_set(bset)

    """
    self.print('{')
    self._indent += 1
    self.print(self.attr('rank', 'same'))
    self.print(self.node(key, group=key))
    for bset in op.build_sets:
      self.print(self.node(self.key_of(bset), group=key))
    self._indent -= 1
    self.print('}')
    """

    self._indent -= 1
    self.print('}')

  def handle_build_set(self, bset):
    if bset in self._seen:
      return
    self._seen.add(bset)
    key = self.key_of(bset)

    self.print('subgraph "cluster_{}" {{'.format(key))
    self._indent += 1
    self.print(self.attr('label', ''))
    self.print(self.attr('labeljust', 'l'))
    self.print(self.attr('style', 'filled,rounded'))
    self.print(self.attr('fillcolor', 'goldenrod2'))
    self.print(self.attr('color', 'goldenrod4'))

    for fset in bset.inputs.values():
      self.handle_file_set(fset)
    for fset in bset.outputs.values():
      self.handle_file_set(fset)

    self._indent -= 1
    self.print('}')

  def handle_file_set(self, fset):
    if fset in self._seen:
      return
    self._seen.add(fset)
    key = self.key_of(fset)
    alias = ', '.join(fset.aliases)
    lines = ([alias] if alias else []) + [repr([nr.fs.base(x) for x in fset])]
    attrs = {'label': '\n'.join(lines), 'fillcolor': 'chocolate1', 'color': 'chocolate3'}
    self.print(self.node(key, **attrs))
    for bset in fset._build_sets_in: self.handle_build_set(bset)
    for bset in fset._build_sets_out: self.handle_build_set(bset)
    for other in fset.inputs:
      self.handle_file_set(other)
      self.print(self.edge(self.key_of(other), key))


def dump_graphviz(obj, fp=None, to_str=False, build_sets_outside=False,
                  exporter_class=GraphvizExporter):
  if to_str:
    fp = io.StringIO()

  exp = exporter_class(fp)
  exp.preamble()

  if isinstance(obj, Master):
    if build_sets_outside:
      for bset in topo_sort(obj):
        #if not bset.operator:
        exp.handle_build_set(bset)
    exp.handle_master(obj)
  elif isinstance(obj, Target):
    exp.handle_target(obj)
  elif isinstance(obj, Operator):
    exp.handle_operator(obj)
  elif isinstance(obj, BuildSet):
    epx.handle_build_set(obj)
  else:
    raise TypeError(type(obj))

  exp.epilogue()

  if to_str:
    return fp.getvalue()


def topo_sort(master):
  """
  Topologically sort all build sets in the build graph from the connections
  between file sets.
  """

  from nr.stream import stream

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
        bset_inputs[bset] = set(stream.concat(x._build_sets_out.keys() for x in bset.inputs.values()))
        bset_reverse.setdefault(bset, set())
        for x in bset_inputs[bset]:
          bset_reverse.setdefault(x, set()).add(bset)
        if not bset_inputs[bset]:
          bset_start.add(bset)
        queue += bset_inputs[bset]

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
    for files in build_set.outputs.values():
      for filename in files:
        nr.fs.makedirs(nr.fs.dir(filename))
    commands = build_set.get_commands()
    for cmd in commands:
      print('  $', ' '.join(shlex.quote(x) for x in cmd))
      subprocess.check_call(cmd)

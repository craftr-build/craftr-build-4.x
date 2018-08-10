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
BuildSets. A BuildSet is a collection of named input and output file lists as
well as variables that are substituted in the operators command list.

The files in a BuildSet are tracked globally in the build Master. A file may
only be listed once in the outputs of a BuildSet.
"""

__all__ = ['BuildSet', 'Commands', 'Operator', 'Target', 'Master']

import io
import nr.fs
import re
import shlex
import subprocess

from nr.types.map import ChainMap, ValueIterableMap
from nr.stream import stream
from typing import List
from .template import TemplateCompiler


class BuildSet:
  """
  A build set is a collection of named sets of files and variables that
  represent an instantiation of the build action templated by an #Operator.

  The output files in a build set must be registered to the build #Master.
  This is done automatically when adding files to the set.
  """

  def __init__(self, master:'Master', description:str=None):
    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    if description is not None and not isinstance(description, str):
      raise TypeError('expected str, got {}'.format(type(description).__name__))
    self._master = master
    self._description = description
    self._inputs = {}
    self._outputs = {}
    self._variables = {}
    self._operator = None

  def __repr__(self):
    return 'BuildSet(operator={}, inputs={}, outputs={}, variables={})'\
      .format(type(self).__name__, self.operator, set(self._inputs.keys()),
              set(self._outputs.keys()), set(self._variables.keys()))

  @property
  def master(self):
    return self._master

  @property
  def description(self):
    return self._description

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
  def operator(self):
    return self._operator

  def add_input_files(self, set_name:str, files:List[str]):
    result = []
    dest = self._inputs.setdefault(set_name, [])
    for x in files:
      x = self._master.canonicalize_path(x)
      result.append(x)
      dest.append(x)
    return result

  def add_output_files(self, set_name:str, files:List[str]):
    result = []
    dest = self._outputs.setdefault(set_name, [])
    for x in files:
      x = self._master.canonicalize_path(x)
      self._master._declare_output(self, x)
      result.append(x)
      dest.append(x)
    return result

  def get_input_build_sets(self) -> set:
    inputs = set()
    for fname in stream.concat(self.inputs.values()):
      bset = self._master._output_files.get(fname, None)
      if bset is not None:
        inputs.add(bset)
    return inputs

  def get_commands(self):
    """
    Return the expanded commands for the build set from the operator.
    This method raises a #RuntimeError if the build set is not attached
    to an operator.
    """

    if not self._operator:
      raise TypeError('build set is not attached to an operator')
    variables = ChainMap(self._variables, self._operator._variables)
    return self._operator._commands.compiled.render(
      self._inputs, self._outputs, variables)

  def get_description(self):
    """
    Return the description of the build set with variables expanded.
    """

    if not self._operator:
      return self._description
    template = TemplateCompiler().compile_list(shlex.split(self._description))
    variables = ChainMap(self._variables, self._operator._variables)
    return ' '.join(template.render(self._inputs, self._outputs, variables))


class Commands:
  """
  This class represents a list of system commands, where every system command
  is a list of strings. The strings in the commands are compiled using a
  #TemplateCompiler and stored only in the compiled form.

  A commands object is immutable after construction.
  """

  def __init__(self, commands:List[List[str]]):
    self._commands = commands
    self._compiled = TemplateCompiler().compile_commands(commands)
    self._inputs, self._outputs, self._variables = \
        self._compiled.occurences(set(), set(), set())

  def __repr__(self):
    return 'Commands({})'.format(self._commands)

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
  def compiled(self):
    return self._compiled


class Operator:
  """
  An operator defines one or more system commands that is executed to produce
  output files from input files. These files are declared in a #BuildSet that
  must be attached to the operator.
  """

  def __init__(self, master:'Master', id:str, commands:Commands,
               explicit:bool=False, syncio:bool=False):
    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    if not isinstance(id, str):
      raise TypeError('expected str, got {}'.format(type(id).__name__))
    if not id:
      raise ValueError('id must not be empty')
    if not isinstance(commands, Commands):
      raise TypeError('expected Commands, got {}'.format(type(commands).__name__))

    self._id = id
    self._master = master
    self._commands = commands
    self._target = None
    self._build_sets = []
    self._variables = {}
    self._explicit = explicit
    self._syncio = syncio

  def __repr__(self):
    return 'Operator(target={!r}, id={!r}))'.format(self._target, self._id)

  @property
  def master(self):
    return self._master

  @property
  def id(self):
    return self._id

  @property
  def commands(self):
    return [x[:] for x in self._commands]

  @property
  def variables(self):
    return self._variables

  @property
  def target(self):
    return self._target

  @property
  def explicit(self):
    return self._explicit

  @property
  def syncio(self):
    return self._syncio

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
    for set_name in self._commands.inputs:
      if set_name not in build_set.inputs:
        raise RuntimeError('operator requires ${{<{}}} which is not '
                           'provided by this build set'.format(set_name))
    for set_name in self._commands.outputs:
      if set_name not in build_set.outputs:
        raise RuntimeError('operator requires ${{@{}}} which is not '
                           'provided by this build set'.format(set_name))
    for var_name in self._commands.variables:
      if var_name not in self._variables and var_name not in build_set._variables:
        raise RuntimeError('operator requires ${{{}}} which is not provided '
                           'by this build set'.format(var_name))
    self._build_sets.append(build_set)
    return build_set


class Target:
  """
  A target is a collection of operators.
  """

  def __init__(self, master:'Master', id:str):
    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    if not isinstance(id, str):
      raise TypeError('expected str, got {}'.format(type(id).__name__))
    if not id:
      raise ValueError('id must not be empty')

    self._id = id
    self._master = master
    self._operators = {}

  def __repr__(self):
    return '<Target id={!r}>'.format(self._id)

  @property
  def id(self):
    return self._id

  @property
  def master(self):
    return self._master

  @property
  def operators(self):
    return ValueIterableMap(internal=self._operators)

  def add_operator(self, operator):
    if not isinstance(operator, Operator):
      raise TypeError('expected Operator, got {}'.format(
        type(operator).__name__))
    if operator._target is None:
      operator._target = self
    if operator._target is not self:
      raise RuntimeError('add_operator(): Operator belongs to another target')
    if operator._id in self._operators:
      raise TypeError('Operator id {!r} already occupied in Target {!r}'
        .format(operator._id, self._id))
    self._operators[operator._id] = operator
    return operator


class Master:
  """
  This class keeps track of targets and the files embedded in the build graph
  and also provides some behaviour to the build graph with the #substitutor
  member and the #canonicalize_path() method.
  """

  def __init__(self, template_compiler:TemplateCompiler=None):
    self._template_compiler = template_compiler or TemplateCompiler()
    self._targets = {}
    self._output_files = {}  # Maps from the canonical filename to a BuildSet

  @property
  def template_compiler(self):
    return self._template_compiler

  def canonicalize_path(self, path):
    """
    Canonicalize the specified *path*, turning it absolute and reducing it
    to the most relevant and normalized form. The default implementation
    acts as an alias to #nr.fs.canonical().
    """

    return nr.fs.canonical(path)

  @property
  def targets(self):
    return ValueIterableMap(internal=self._targets)

  def add_target(self, target):
    if not isinstance(target, Target):
      raise TypeError('expected Target, got {}'.format(type(target).__name__))
    if target._id in self._targets:
      raise ValueError('Target id {!r} already occupied'.format(target._id))
    self._targets[target._id] = target
    return target

  def _declare_output(self, build_set:BuildSet, filename:str):
    # Note: filename must be canonicalized
    assert self.canonicalize_path(filename) == filename
    if filename in self._output_files:
      raise ValueError('Two build sets with the same output file can not '
                       'co-exist ({}, filename={!r})'.format(build_set, filename))
    self._output_files[filename] = build_set


def to_graph(master):
  from craftr.utils import graphviz as G
  g = G.Graph(bidirectional=False)
  g.setting('graph', fontsize=10, fontname='monospace')
  g.setting('node', shape='record', style='filled', fontsize=10, fontname='monospace')

  def file_node(filename, cluster):
    ident = 'File:{}'.format(filename)
    if ident in g.nodes:
      return g.nodes[ident]
    return g.node(ident, cluster, label=nr.fs.base(filename))

  for target in master.targets:
    target_cluster = g.cluster(target.id,
      label='Target: {}'.format(target.id), labeljust='l')
    for operator in target.operators:
      op_cluster = target_cluster.subcluster('{}@{}'.format(target.id, operator.id),
        label='Operator: {}@{}'.format(target.id, operator.id))
      for build_set in operator.build_sets:
        build_cluster = op_cluster.subcluster(
          id='BuildSet:{}'.format(id(build_set)), label='',
          style='filled', fillcolor='grey')
        for set_name, files in build_set.outputs.items():
          set_cluster = build_cluster.subcluster(
            id='{}/@{}'.format(build_cluster.id, set_name),
            label='@{}'.format(set_name))
          [file_node(x, set_cluster) for x in files]
        for set_name, files in build_set.inputs.items():
          set_cluster = build_cluster.subcluster(
            id='{}/<{}'.format(build_cluster.id, set_name),
            label='<{}'.format(set_name))
          [file_node(x, set_cluster) for x in files]

  # TODO: (How to do) edges like input_file->BuildSetCluster->output_file ??

  return g


def topo_sort(master):
  """
  Topologically sort all build sets in the build graph from the connections
  between file sets.
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
        bset_inputs[bset] = bset.get_input_build_sets()
        bset_reverse.setdefault(bset, set())
        for x in bset_inputs[bset]:
          bset_reverse.setdefault(x, set()).add(bset)
        if not bset_inputs[bset]:
          bset_start.add(bset)
        else:
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

  for build_set in topo_sort(master):
    if not build_set.operator:
      continue

    prefix = '[{}/{}]'.format(build_set.operator.target.id, build_set.operator.id)

    # Skip the build set if all output files are newer than the input files.
    infiles = list(stream.concat(build_set.inputs.values()))
    outfiles = list(stream.concat(build_set.outputs.values()))
    if not nr.fs.compare_all_timestamps(infiles, outfiles):
      print(prefix, 'SKIP')
      continue

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

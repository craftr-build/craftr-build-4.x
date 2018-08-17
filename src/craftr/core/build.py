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

import collections
import contextlib
import hashlib
import io
import json
import os
import nr.fs
import re
import shlex
import subprocess

from nr.types.map import ChainMap, ValueIterableMap
from nr.stream import stream
from typing import Dict, Iterable, List, Union
from .template import TemplateCompiler


class BuildSet:
  """
  A build set is a collection of named sets of files and variables that
  represent an instantiation of the build action templated by an #Operator.

  The output files in a build set must be registered to the build #Master.
  This is done automatically when adding files to the set.
  """

  def __init__(self, master: 'Master', description: str = None,
               environ: Dict[str, str] = None, cwd: str = None,
               depfile: str = None):
    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    if description is not None and not isinstance(description, str):
      raise TypeError('expected str, got {}'.format(type(description).__name__))
    if depfile is not None and not isinstance(depfile, str):
      raise TypeError('expected str, got {}'.format(type(depfile).__name__))
    self._master = master
    self.description = description
    self._environ = environ
    self._cwd = cwd or None  # empty string is invalid, fallback to None
    self.depfile = depfile
    self._inputs = {}
    self._outputs = {}
    self._variables = {}
    self._operator = None

  def __repr__(self):
    return '{}(operator={}, inputs={}, outputs={}, variables={})'\
      .format(type(self).__name__, self.operator, set(self._inputs.keys()),
              set(self._outputs.keys()), set(self._variables.keys()))

  @property
  def master(self):
    return self._master

  @property
  def environ(self):
    return self._environ

  @property
  def cwd(self):
    return self._cwd

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

  def add_input_files(self, set_name: str, files: List[str]):
    result = []
    dest = self._inputs.setdefault(set_name, [])
    for x in files:
      x = self._master.canonicalize_path(x)
      result.append(x)
      dest.append(x)
    return result

  def add_output_files(self, set_name: str, files: List[str]):
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
    return self._operator.commands.render(self._inputs, self._outputs, variables)

  def get_description(self):
    """
    Return the description of the build set with variables expanded.
    """

    if not self.description:
      return ' && '.join(' '.join(map(shlex.quote, x)) for x in self.get_commands())
    if not self._operator:
      return self.description
    template = TemplateCompiler().compile_list(shlex.split(self.description))
    variables = ChainMap(self._variables, self._operator._variables)
    return ' '.join(template.render(self._inputs, self._outputs, variables))

  def get_environ(self):
    return ChainMap(self._environ or {}, self._operator.environ or {})

  def get_cwd(self):
    return self._cwd or self._operator.cwd

  def to_json(self):
    return {'description': self.description, 'environ': self._environ,
            'cwd': self._cwd, 'depfile': self.depfile,
            'inputs': self._inputs, 'outputs': self._outputs,
            'variables': self._variables}

  @classmethod
  def from_json(cls, master: 'Master', operator: 'Operator', data: Dict):
    self = object.__new__(cls)
    self._master = master
    self.description = data['description']
    self._environ = data['environ']
    self._cwd = data['cwd']
    self.depfile = data['depfile']
    self._inputs = data['inputs']
    self._outputs = data['outputs']
    self._variables = data['variables']
    self._operator = operator
    [master._declare_output(self, x) for x in stream.concat(self.outputs.values())]
    return self

  def compute_hash(self):
    """
    Computes a hash for the build set.
    """

    data = self.to_json()
    data['commands'] = self.operator.commands.to_json()
    data['environ'] = dict(self.get_environ())
    data['cwd'] = self.get_cwd()
    return hashlib.sha1(json.dumps(data, sort_keys=True).encode('utf8')).hexdigest()


class Command:
  """
  Represents a single command.
  """

  def __init__(self, command: Union[List[str], str],
               supports_response_file: bool = False,
               response_args_begin: int = 1):
    if isinstance(command, str):
      command = shlex.split(command)
    self._command = command
    self._compiled = TemplateCompiler().compile_list(command)
    self._inputs, self._outputs, self._variables = \
        self._compiled.occurences(set(), set(), set())
    self._supports_response_file = supports_response_file
    self._response_args_begin = response_args_begin

  def __repr__(self):
    return 'Command({!r})'.format(self._command)

  def __iter__(self):
    return iter(self._command)

  @property
  def command(self):
    return self._command[:]

  @property
  def compiled(self):
    return self._compiled

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
  def supports_response_file(self):
    return self._supports_response_file

  @property
  def response_args_begin(self):
    return self._response_args_begin

  def render(self, inputs, outputs, variables):
    return self._compiled.render(inputs, outputs, variables)

  @contextlib.contextmanager
  def with_response_file(self, commands):
    """
    Takes a rendered list of commands and produces a response file on Windows
    if necessary and supported by the command. The *commands* should be the
    result of the command's #render() method.
    """

    if not self.supports_response_file:
      yield commands; return

    # Create a response file on Windows if supported by the command.
    if os.name == 'nt' and sum(len(x)+1 for x in commands) > 8192:
      with nr.fs.tempfile(text=True, encoding='utf16') as fp:
        fp.write('\n'.join(commands[self.response_args_begin:]))
        fp.write('\n')
        fp.close()
        yield commands[:self.response_args_begin] + ['@' + fp.name]
    else:
      yield commands

  def to_json(self):
    return {
      'command': self._command,
      'supports_response_file': self._supports_response_file,
      'response_args_begin': self._response_args_begin
    }

  @classmethod
  def from_json(cls, data):
    return cls(data['command'], data['supports_response_file'],
      data['response_args_begin'])


class Commands:
  """
  This class represents a list of system commands, where every system command
  is a list of strings. The strings in the commands are compiled using a
  #TemplateCompiler and stored only in the compiled form.

  A commands object is immutable after construction.
  """

  def __init__(self, commands: List[Union[Command, List[str]]]):
    self._commands = []
    for x in commands:
      if not isinstance(x, Command):
        x = Command(x)
      self._commands.append(x)
    self._inputs, self._outputs, self._variables = set(), set(), set()
    [x.compiled.occurences(self._inputs, self._outputs, self._variables)
     for x in self._commands]

  def __repr__(self):
    return 'Commands({!r})'.format(self._commands)

  def __iter__(self):
    return (x for x in self._commands)

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

  def render(self, inputs, outputs, variables):
    return [x.render(inputs, outputs, variables) for x in self._commands]

  def to_json(self) -> List:
    return [x.to_json() for x in self._commands]

  @classmethod
  def from_json(cls, data: List):
    return cls([Command.from_json(x) for x in data])


class Operator:
  """
  An operator defines one or more system commands that is executed to produce
  output files from input files. These files are declared in a #BuildSet that
  must be attached to the operator.
  """

  def __init__(self, master: 'Master', name: str, commands: Commands,
               environ: Dict[str, str] = None, cwd: str = None,
               explicit: bool = False, syncio: bool = False,
               deps_prefix: str = None, restat: bool = False):

    if not isinstance(master, Master):
      raise TypeError('expected Master, got {}'.format(type(master).__name__))
    if not isinstance(name, str):
      raise TypeError('expected str, got {}'.format(type(name).__name__))
    if not name:
      raise ValueError('name must not be empty')
    if not isinstance(commands, Commands):
      raise TypeError('expected Commands, got {}'.format(type(commands).__name__))
    if deps_prefix is not None and not isinstance(deps_prefix, str):
      raise TypeError('expected str, got {}'.format(type(deps_prefix).__name__))
    self._name = name
    self._master = master
    self._commands = commands
    self._target = None
    self._build_sets = []
    self._variables = {}
    self._environ = environ
    self._cwd = cwd or None  # empty string is invalid, fallback to None
    self._explicit = explicit
    self._syncio = syncio
    self._deps_prefix = deps_prefix
    self._restat = restat

  def __repr__(self):
    return 'Operator(target={!r}, name={!r}))'.format(self._target, self._name)

  @property
  def master(self):
    return self._master

  @property
  def id(self):
    return self._target.id + '@' + self._name

  @property
  def name(self):
    return self._name

  @property
  def commands(self):
    return self._commands

  @property
  def variables(self):
    return self._variables

  @property
  def target(self):
    return self._target

  @property
  def environ(self):
    return self._environ

  @property
  def cwd(self):
    return self._cwd

  @property
  def explicit(self):
    return self._explicit

  @property
  def syncio(self):
    return self._syncio

  @property
  def deps_prefix(self):
    return self._deps_prefix

  @property
  def restat(self):
    return self._restat

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

  def to_json(self, *, build_sets: List[BuildSet] = None) -> Dict:
    if build_sets is None:
      build_sets = self._build_sets
    return {'name': self._name, 'commands': self._commands.to_json(),
            'build_sets': [x.to_json() for x in build_sets],
            'variables': self._variables, 'environ': self._environ,
            'cwd': self._cwd, 'explicit': self._explicit,
            'syncio': self._syncio, 'deps_prefix': self._deps_prefix}

  @classmethod
  def from_json(cls, master: 'Master', target: 'Target', data: Dict):
    self = object.__new__(cls)
    self._master = master
    self._target = target
    self._name = data['name']
    self._commands = Commands.from_json(data['commands'])
    self._build_sets = [BuildSet.from_json(master, self, x) for x in data['build_sets']]
    self._variables = data['variables']
    self._environ = data['environ']
    self._cwd = data['cwd']
    self._explicit = data['explicit']
    self._syncio = data['syncio']
    self._deps_prefix = data['deps_prefix']
    return self


class Target:
  """
  A target is a collection of operators.
  """

  def __init__(self, master: 'Master', id: str):
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
    if operator._name in self._operators:
      raise TypeError('Operator id {!r} already occupied in Target {!r}'
        .format(operator._name, self._id))
    self._operators[operator._name] = operator
    return operator

  def to_json(self, *, operators: List[Operator] = None) -> Dict:
    if operators is None:
      operators = self._operators.values()
    return {'id': self._id, 'operators': [x.to_json() for x in operators]}

  @classmethod
  def from_json(cls, master: 'Master', data: Dict) -> 'Target':
    self = object.__new__(cls)
    self._master = master
    self._id = data['id']
    self._operators = {x['name']: Operator.from_json(master, self, x)
                       for x in data['operators']}
    return self


class Master:
  """
  This class keeps track of targets and the files embedded in the build graph
  and also provides some behaviour to the build graph with the #substitutor
  member and the #canonicalize_path() method.
  """

  def __init__(self, template_compiler: TemplateCompiler = None):
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

  def all_operators(self) -> Iterable[Operator]:
    for target in self.targets:
      yield from target.operators

  def all_build_sets(self) -> Iterable[BuildSet]:
    for op in self.all_operators():
      yield from op.build_sets

  def to_json(self):
    return [x.to_json() for x in self._targets.values()]

  def load_json(self, data: Dict):
    self._targets = {x['id']: Target.from_json(self, x) for x in data}

  def save(self, filename: str):
    with open(filename, 'w') as fp:
      json.dump(self.to_json(), fp, sort_keys=True)

  def load(self, filename: str):
    with open(filename) as fp:
      data = json.load(fp)
    self.load_json(data)


def to_graph(master):
  from craftr.utils import graphviz as G
  g = G.Graph(bidirectional=False)
  g.setting('graph', fontsize=10, fontname='monospace')
  g.setting('node', shape='record', style='filled', fontsize=10, fontname='monospace')

  def file_node(filename, cluster=None):
    ident = 'File:{}'.format(filename)
    if ident in g.nodes:
      return g.nodes[ident]
    return g.node(ident, cluster, label=nr.fs.base(filename))

  def bset_node(bset, cluster=None):
    # Add all this information in the identifier as it is displayed in the
    # browser when hovering over the SVG element.
    label = '\n'.join(' '.join(map(shlex.quote, x)) for x in bset.operator.commands)
    ident = 'BuildSet:{}\nOperator: {}\n'.format(id(bset), bset.operator.id) + '\n' + label
    if ident in g.nodes:
      return g.nodes[ident]
    return g.node(ident, cluster, label='', shape='circle', fixedsize='true',
      width='0.2', color='brown4', fillcolor='brown3')

  def target_cluster(target):
    return None
    ident = 'Target:{}'.format(target.id)
    if ident in g.clusters:
      return g.clusters[ident]
    return g.cluster(ident)

  def op_cluster(op, cluster=None):
    return None
    ident = 'Operator:{}'.format(op.id)
    if ident in g.clusters:
      return g.clusters[ident]

    if cluster is None:
      cluster = target_cluster(op.target)

    cluster = g.cluster(ident, cluster, label='', xlabel='foo',
      fillcolor='azure2', color='azure3', style='filled')

    return cluster

  bsets = []
  for target in master.targets:
    for op in target.operators:
      for bset in op.build_sets:
        if not bset.outputs: continue
        bsets.append(bset)

  #for target in master.targets:
  #  for op in target.operators:
  #    cluster = g.cluster('Operator:{}'.format(op.id))
  #    for bset in op.build_sets:
  #      bset_node(bset, cluster)

  for bset in bsets:
    if not bset.outputs: continue
    node = bset_node(bset)
    for f in stream.concat(bset.inputs.values()):
      g.edge(file_node(f).id, node.id)
    for f in stream.concat(bset.outputs.values()):
      g.edge(node.id, file_node(f, op_cluster(bset.operator)).id)

  return g


def topo_sort(build_sets: Union[Master, List[BuildSet]]):
  """
  Topologically sort the build sets in the specified list.

  If a #Master is specified, all build sets of that build master that are
  not explicit are used.
  """

  if isinstance(build_sets, Master):
    build_sets = [x for x in build_sets.all_build_sets()
                  if not x.operator.explicit]

  # A mirror of the inputs for every build set, allowing us to remove
  # edge for this algorithm without actually modifying the graph.
  bset_inputs = {}

  # A dictionary that reverses the dependencies between build sets.
  bset_reverse = {}

  # A set of build sets that have no input.
  bset_start = set()

  queue = collections.deque(build_sets)
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

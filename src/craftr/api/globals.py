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
This module implements the API for the Craftr build scripts.

Craftr build scripts are plain Python scripts that import the members of
this module to generate a build graph. The functions in this module are based
on a global thread local that binds the current build graph master, target,
etc. so they do not have to be explicitly declared and passed around.
"""

__all__ = ['session', 'target', 'build_set', 'transform']

import contextlib
import shlex

from .session import Session, BuildSet, Target
from typing import List, Union
from werkzeug.local import LocalStack, LocalProxy

_session_stack = LocalStack()
session = LocalProxy(lambda: _session_stack.top)


@contextlib.contextmanager
def target(name):
  """
  Creates a new target in the current scope and sets it active. The function
  must be used as a context-manager. Nesting multiple calls to this function
  in the same scope is not allowed and raises a #RuntimeError.
  """

  if session.current_scope.current_target:
    raise RuntimeError('nesting target()s in the same scope is not allowed')

  target = Target(session(), session.current_scope, name)
  with session.current_scope.enter_target(target):
    yield target


def build_set(alias=None, inputs=None, **file_sets):
  """
  Creates a new build set in the current target that will be streamed into
  the next operator. The currently selected build sets can be retrievd with
  #selected_build_sets() and modified with #select_build_sets().
  """

  bset = BuildSet(alias, session.build_master, inputs or [])
  for key, value in file_sets.items():
    if isinstance(value, str):
      bset.variables[key] = value
    else:
      bset.add_files(key, value)

  target = session.current_scope.current_target
  target.add_build_set(bset)
  target.current_build_sets.add(bset)
  return bset


def transform(name: str, update: Union[str, callable],
              command: Union[str, List[str]] = None,
              commands: Union[List[str], List[List[str]]] = None,
              for_each: bool = False):
  """
  Creates an operator that transforms the currently selected build sets
  using the specified *command* or *commands*.
  """

  if isinstance(update, str):
    update = eval('lambda x: '+  update)

  if command:
    if isinstance(command, str):
      command = shlex.split(command)
    commands = [command]
  elif commands:
    for i, x in enumerate(commands):
      if isinstance(x, str):
        commands[i] = shlex.split(x)

  subst = session.build_master.behaviour.get_substitutor()
  in_sets, out_sets, vars = subst.multi_occurences(commands)

  if len(in_sets) != 1:
    raise ValueError('need exactly one input set')
  if len(out_sets) != 1:
    raise ValueError('need exactly one output set')
  in_set = next(iter(in_sets))
  out_set = next(iter(out_sets))


  target = session.current_scope.current_target
  files = [y for x in target.current_build_sets for y in x.get_file_set(in_set)]
  out_files = [update(x) for x in files]
  build_sets = []

  if for_each:
    for infile, outfile in zip(files, out_files):
      inset = BuildSet(None, session.build_master, target.current_build_sets)
      inset.add_files(in_set, [infile])
      outset = BuildSet(None, session.build_master, [inset])
      outset.add_files(out_set, [outfile])
      build_sets.append(outset)
  else:
    outset = BuildSet(None, session.build_master, target.current_build_sets)
    outset.add_files(out_set, out_files)
    build_sets.append(outset)

  from craftr.core.build import Operator
  op = target.add_operator(Operator(name, session.build_master, commands))
  [op.add_build_set(x) for x in build_sets]

  target.current_build_sets = set(build_sets)

  return op

  #out_files = []
  #for filename in set(*zip(
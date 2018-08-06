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

#__all__ = ['session', 'target', 'build_set', 'transform']


import contextlib
from craftr.core import build as _build


class Session(_build.Master):

  def __init__(self, behaviour = None):
    super().__init__(behaviour or _build.Behaviour())
    self._current_scopes = []

  @contextlib.contextmanager
  def enter_scope(self, name):
    self._current_scopes.append({'name': name, 'target': None})
    try: yield
    finally:
      assert self._current_scopes.pop()['name'] == name

  def current_scope(self):
    return self._current_scopes[-1] if self._current_scopes else None


class Target(_build.Target):

  def __init__(self, name):
    super().__init__(name, current_session())
    self._current_buildset = None

  def current_buildset(self):
    return self._current_buildset


class Operator(_build.Operator):

  def __init__(self, name, commands):
    super().__init__(name, current_session(), commands)


_session = None

def current_session():
  return _session

def current_scope():
  return _session.current_scope()

def current_target():
  return current_scope()['target']

def current_buildset():
  return current_target().current_buildset()


def target(name):
  scope = current_scope()
  target = current_session().add_target(Target(scope['name'] + '@' + name))
  current_scope()['target'] = target
  return target

def buildset(**kwargs):
  """
  Creates a new #~_build.BuildSet that is set as the current build set in
  the current target. This is the build set that will be used by functions
  that produce operators.

  inputs (list of BuildSet): A list of build sets that this one depends on.
  description (str): The description of the build set, only import for build
    sets that are attached to operators.
  from_ (list of BuildSet): A list of build sets that will be joined in the
    new build set. They will also be used as inputs.
  kwargs (list of str): A list of filenames to add to the build set.
  """

  bset = new_buildset(**kwargs)
  current_target()._current_buildset = bset
  return bset

def new_buildset(*, inputs=(), description=None, from_=(), **kwargs):
  bset = _build.BuildSet(current_session(), inputs, description)
  for key, value in kwargs.items():
    if isinstance(value, str):
      bset.variables[key] = value
    else:
      bset.add_files(key, value)
  [bset.add_from(x) for x in from_]
  return bset

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

__all__ = [
  'Session',
  'Scope',
  'Target',
  'Operator',
  'BuildSet',
  'session',
  'create_target',
  'create_build_set',
  'glob'
]

import contextlib
import nr.fs

from craftr.core import build as _build

session = None  # The current #Session


class Session(_build.Master):
  """
  This is the root instance for a build session. It introduces a new virtual
  entity called a "scope" that is created for every build script. Target names
  will be prepended by that scope, relative paths are treated relative to the
  scopes current directory and every scope gets its own build output directory.
  """

  def __init__(self, build_directory: str,
               behaviour: _build.Behaviour = None):
    super().__init__(behaviour or _build.Behaviour())
    self._build_directory = nr.fs.canonical(build_directory)
    self._current_scopes = []
    self._build_sets = []  # Registers all build sets

  @contextlib.contextmanager
  def enter_scope(self, name, version, directory):
    scope = Scope(self, name, version, directory)
    self._current_scopes.append(scope)
    try: yield
    finally:
      assert self._current_scopes.pop() is scope

  @property
  def current_scope(self):
    return self._current_scopes[-1] if self._current_scopes else None

  @property
  def current_target(self):
    if self._current_scopes:
      return self._current_scopes[-1].current_target
    return None

  # _build.Master

  def event(self, name: str, data: object):
    if name == 'dump_graphviz':
      [data['handle_build_set'](x, data['indent']) for x in self._build_sets]


class Scope:
  """
  A scope basically represents a Craftr build module. The name of a scope is
  usually determined by the Craftr module loader.
  """

  def __init__(self, session: Session, name: str, version: str, directory: str):
    self.session = session
    self.name = name
    self.version = version
    self.directory = directory
    self.current_target = None

  @property
  def build_directory(self):
    return nr.fs.join(self.session.build_directory, self.name)


class Target(_build.Target):
  """
  Extends the graph target class by a property that describes the active
  build set that is supposed to be used by the next function that creates an
  operator.
  """

  def __init__(self, name: str):
    super().__init__(name, session)
    self.current_build_set = None

  def new_operator(self, *args, **kwargs):
    return self.add_operator(Operator(*args, **kwargs))


class Operator(_build.Operator):
  """
  Extends the graph operator class so that the build master does not need
  to be passed explicitly.
  """

  def __init__(self, name, commands):
    super().__init__(name, session, commands)

  def new_build_set(self, **kwargs):
    return self.add_build_set(BuildSet(**kwargs))


class BuildSet(_build.BuildSet):
  """
  Extends the graph BuildSet class so that the build master does not need to
  be passed explicitly and supporting some additional parameters for
  convenient construction.
  """

  def __init__(self, inputs: list = (),
               from_: list = None,
               description: str = None,
               alias: str = None,
               **kwargs):
    super().__init__(session, (), description, alias)
    for bset in (from_ or ()):
      self.add_from(bset)
    if from_ is not None:
      # Only take into account BuildSets in the inputs that are not
      # already dependend upon transitively. This is to reduce the
      # number of connections (mainly for a nice Graphviz representation)
      # between build sets while keeping the API as simple as passing both
      # the from_ and inputs parameters.
      for x in inputs:
        if not self._has_transitive_input(self, x):
          self._inputs.add(x)
    else:
      self._inputs.update(inputs)
    for key, value in kwargs.items():
      if isinstance(value, str):
        self._variables[key] = value
      else:
        self.add_files(key, value)
    session._build_sets.append(self)

  @classmethod
  def _has_transitive_input(cls, self, build_set):
    for x in self._inputs:
      if build_set is x:
        return True
      if cls._has_transitive_input(x, build_set):
        return True
    return False


# API for declaring targets

def create_target(name):
  """
  Create a new target with the specified *name* in the current scope and
  set it as the current target.
  """

  scope = session.current_scope
  target = session.add_target(Target(scope.name + '@' + name))
  scope.current_target = target
  return target


def create_build_set(**kwargs):
  """
  Creates a new #BuildSet and sets it as the current build set in the current
  target.
  """

  bset = BuildSet(**kwargs)
  session.current_target.current_build_set = bset
  return bset


# Path API that takes the current scope's directory as the
# current "working" directory.

def glob(patterns, parent=None, excludes=None, include_dotfiles=False,
         ignore_false_excludes=False):
  if not parent:
    parent = session.current_scope.directory
  return nr.fs.glob(patterns, parent, excludes, include_dotfiles,
                    ignore_false_excludes)

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

import contextlib

from craftr4.core.build import Master, BuildSet as _BuildSet, Target as _Target


class Session:

  def __init__(self, build_master: Master = None):
    self._build_master = build_master or Master()
    self._scopes = {}
    self._scope_stack = []

  def __call__(self):
    return self

  @property
  def build_master(self):
    return self._build_master

  @property
  def scopes(self):
    return self._scopes.values()

  @property
  def current_scope(self):
    return self._scope_stack[-1] if self._scope_stack else None

  @contextlib.contextmanager
  def enter_scope(self, name, version):
    if name in self._scopes:
      raise ValueError('Scope {!r} already exists'.format(name))
    scope = self._scopes[name] = Scope(self, name, version)
    self._scope_stack.append(scope)
    try: yield
    finally:
      assert self._scope_stack.pop() is scope

  def get_scope(self, name: str):
    return self._scopes[name]


class Scope:

  def __init__(self, session: Session, name: str, version: str):
    self.name = name
    self.version = version
    self._session = session
    self._targets = {}
    self._target_stack = []

  @property
  def session(self):
    return self._session

  @property
  def targets(self):
    return self._targets.values()

  @property
  def current_target(self):
    return self._target_stack[-1] if self._target_stack else None

  @contextlib.contextmanager
  def enter_target(self, target: 'Target'):
    if target.basename in self._targets:
      raise ValueError('Scope {!r} already has a target named {!r}'
        .format(self.name, target.name))
    self._session.build_master.add_target(target)
    self._targets[target.basename] = target
    self._target_stack.append(target)
    try: yield
    finally: assert self._target_stack.pop() is target

  def get_target(self, name):
    return self._targets[name]


class BuildSet(_BuildSet):

  def __init__(self, alias: str, *args, **kwargs):
    self._alias = alias
    super().__init__(*args, **kwargs)

  @property
  def alias(self):
    return self._alias


class Target(_Target):

  def __init__(self, session: Session, scope: Scope, name: str):
    self._basename = name
    name = '{}@{}'.format(scope.name, name)
    super().__init__(name, session.build_master)
    self._session = session
    self._scope = scope
    self._build_sets = []
    self._build_sets_map = {}
    self.current_build_sets = set()

  @property
  def basename(self):
    return self._basename

  @property
  def session(self):
    return self._session

  @property
  def scope(self):
    return self._scope

  def add_build_set(self, build_set):
    self._build_sets.append(build_set)
    if build_set._alias:
      self._build_sets_map[build_set._alias] = build_set
    return build_set

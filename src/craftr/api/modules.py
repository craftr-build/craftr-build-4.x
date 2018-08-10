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
This module implements the glue for Node.py and Craftr modules.
"""

import nodepy


class MissingRequiredOptionError(RuntimeError):
  pass


class InvalidOptionError(RuntimeError):
  pass


class ModuleOptions:

  def __init__(self, session, scope):
    self._session = session
    self._scope = scope

  def declare(self, name:str, type, default=NotImplemented):
    option_name = self._scope.name + ':' + name
    try:
      value = self._session.options[option_name]
    except KeyError:
      if default is NotImplemented:
        raise MissingRequiredOptionError(self._scope.name, name)
      value = default
    try:
      value = self.adapt(type, value)
    except ValueError as exc:
      raise InvalidOptionError(self._scope.name, name, str(exc))
    setattr(self, name, value)

  def adapt(self, type_cls, value):
    if type_cls == int:
      if isinstance(value, str):
        return int(value)
      elif isinstance(value, int):
        return value
    elif type_cls == bool:
      if isinstance(value, str):
        value = value.lower().strip()
        if value in ('1', 'true', 'on', 'yes'):
          return True
        elif value in ('0', 'false', 'off', 'no'):
          return False
      elif isinstance(value, bool):
        return value
    elif type_cls == str:
      if isinstance(value, str):
        return value
    raise TypeError('expected {}, got {}'.format(type_cls.__name__, type(value).__name__))


class CraftrModule(nodepy.loader.PythonModule):

  def __init__(self, session, *args, is_main=False, **kwargs):
    super().__init__(*args, **kwargs)
    self.is_main = is_main
    self.session = session
    self.scope = None

  def _exec_code(self, code):
    assert self.loaded
    assert isinstance(code, str), type(code)
    from craftr import api
    for name in api.__all__:
      setattr(self.namespace, name, getattr(api, name))
    with self.session.enter_scope(None, None, str(self.directory)) as scope:
      self.scope = scope
      self.namespace.options = ModuleOptions(self.session, self.scope)
      super()._exec_code(code)


class CraftrModuleLoader(nodepy.resolver.StdResolver.Loader):

  def __init__(self, session):
    self.session = session

  def suggest_files(self, context, path):
    if path.suffix == '.craftr':
      yield path
      path = path.with_suffix('')
    else:
      yield path.with_suffix('.craftr')
    path = nodepy.resolver.resolve_link(context, path)
    yield path.joinpath('build.craftr')

  def can_load(self, context, path):
    return path.suffix == '.craftr'

  def load_module(self, context, package, filename):
    return CraftrModule(self.session, context, None, filename)

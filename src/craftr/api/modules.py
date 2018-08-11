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

from typing import Union
from . import proplib


class MissingRequiredOptionError(RuntimeError):
  pass


class InvalidOptionError(RuntimeError):
  pass


class ModuleOptions:
  """
  The #ModuleOptions object is created in the namespace of every Craftr
  module and can be used to easily declare and retrieved typed options.

  Calling the object expects a name, a type name and a default value.
  The type name must be the name of a property type from the
  #craftr.api.proplib module.
  """

  __PROPTYPE_MAP = {
    str: 'String',
    int: 'Integer',
    bool: 'Bool'
  }

  def __init__(self, session, scope):
    self._session = session
    self._scope = scope

  def __repr__(self):
    attrs = ', '.join('{}={!r}'.format(k, v) for k, v in vars(self).items() if not k.startswith('_'))
    return 'ModuleOptions({})'.format(attrs)

  def __call__(self, name: str, prop_type: Union[str, proplib.PropType],
               default = NotImplemented):
    prop_type = self.__PROPTYPE_MAP.get(prop_type, prop_type)
    prop_type = proplib.prop_type(prop_type)
    option_name = self._scope.name + ':' + name
    try:
      value = self._session.options[option_name]
    except KeyError:
      if default is NotImplemented:
        raise MissingRequiredOptionError(self._scope.name, name)
      value = default
    try:
      value = prop_type.coerce(name, value, None)
    except ValueError as exc:
      raise InvalidOptionError(self._scope.name, name, str(exc))
    setattr(self, name, value)


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
      self.namespace.scope = scope
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

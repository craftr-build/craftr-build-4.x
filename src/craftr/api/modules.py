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
import warnings

from nr.stream import stream
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
    self._aliases = []

  def add_scope_alias(self, alias):
    self._aliases.append(alias)

  def __repr__(self):
    attrs = ', '.join('{}={!r}'.format(k, v) for k, v in vars(self).items() if not k.startswith('_'))
    return 'ModuleOptions({})'.format(attrs)

  def __call__(self, *args, **kwargs):
    warnings.warn('ModuleOptions.__call__() is deprecated, use .add() instead',
                  DeprecationWarning, stacklevel=2)
    self.add(*args, **kwargs)

  def add(self, name: str, prop_type: Union[str, proplib.PropType],
          default = NotImplemented):
    prop_type = self.__PROPTYPE_MAP.get(prop_type, prop_type)
    prop_type = proplib.prop_type(prop_type)
    aliases = [self._scope.name, self._scope.name.rpartition('.')[2]]
    for alias in stream.chain(aliases, self._aliases):
      if alias is None: continue
      option_name = alias + ':' + name
      if option_name in self._session.options:
        value = self._session.options[option_name]
        break
    else:
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
    with self.session.enter_scope(self.name, None, str(self.directory)) as scope:
      self.scope = scope
      self.namespace.scope = scope
      self.namespace.options = ModuleOptions(self.session, self.scope)
      super()._exec_code(code)

  @property
  def name(self):
    if self.scope and self.scope.name:
      return self.scope.name
    if self.filename.name.endswith('.craftr'):
      if self.filename.name == 'build.craftr':
        return self.filename.parent.name
      return self.filename.name[:-7]
    return super().name


class CraftrModuleLoader(nodepy.resolver.StdResolver.Loader):

  def __init__(self, session):
    self.session = session

  def suggest_files(self, context, path):
    if path.suffix == '.craftr':
      yield path
      path = path.with_suffix('')
    else:
      yield path.with_name(path.name + '.craftr')
    path = nodepy.resolver.resolve_link(context, path)
    yield path.joinpath('build.craftr')

  def can_load(self, context, path):
    return path.suffix == '.craftr'

  def load_module(self, context, package, filename):
    return CraftrModule(self.session, context, None, filename)


class CraftrLinkResolver(nodepy.base.Resolver):

  def __init__(self):
    self._aliases = {}

  def add_alias(self, alias, module):
    self._aliases[alias] = module

  def resolve_module(self, request):
    r = str(request.string)
    module = self._aliases.get(r)
    if module is not None:
      return module
    stem, base = r.rpartition('/')[::2]
    i = 0
    for i in range(base.count('.')):
      new_string = '/'.join(base.rsplit('.', i+1))
      if stem:
        new_string = stem + '/' + new_string
      new_request = request.copy(string=nodepy.base.RequestString(new_string))
      try:
        return request.context.resolve(new_request)
      except nodepy.base.ResolveError as exc:
        if exc.request != new_request:
          raise
    raise nodepy.base.ResolveError(request, [], [])

# Copyright (c) 2018 Niklas Rosenstein
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
This module extends the Craftr core context methods and members required for
the evaluation of Craftr build modules via the Craftr DSL. The DSL context
creates a child Node.py context with the ability to load Craftr modules.
"""

from nr import path
from nr.strex import Cursor
from nr.datastructures.mappings import ChainDict, MappingFromObject
from nodepy.utils import pathlib

import nodepy
import shutil
import sys
import {CraftrModuleLoader, do_link} from './nodepy_glue'
import core from '../core'
import proplib from '../proplib'

STDLIB_DIR = module.package.directory.joinpath('craftr-stdlib')


class ModuleOptions:

  def __init__(self, name, context):
    self._name = name
    self._data = {}
    self._context = context

  def __repr__(self):
    return 'ModuleOptions({!r}, {!r})'.format(self._name, self._data)

  def __getattr__(self, key):
    try:
      return self._data[key]
    except KeyError:
      raise AttributeError(key)

  def __setattr__(self, key, value):
    if key not in ('_name', '_data', '_context'):
      self._data[key] = value
    else:
      super().__setattr__(key, value)

  def setdefault(self, key, value):
    return self._context.options.setdefault(self._name + ':' + key, value)


class DslModule(core.Module):

  nodepy_module = None

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.options = ModuleOptions(self.name, self.context)

  def init_namespace(self, ns):
    ns.module = self
    ns.options = self.options

  def load_module(self, name):
    mod = self.nodepy_module.require(name + '.craftr', exports=False)
    return mod.craftr_module

  @property
  def scope(self):
    assert self.nodepy_module, "DslModule.nodepy_module is not set"
    return MappingFromObject(self.nodepy_module.namespace)


class DslTarget(core.Target):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._scope = {'target': self}

  @property
  def scope(self):
    return ChainDict(self._scope, self.module.scope)

  def set_props(self, export_or_props, props=None, on_unknown_property='report'):
    """
    set_props(props)
    set_props(export, props)

    Sets properties on the the target. A property may have several prefixes
    to determine the write behaviour.

    * `+`: Append to the existing value.
    * `!`: Write to the exported properties (only really useful with the
      first method signature)
    """

    assert on_unknown_property in ('report', 'raise')

    if props is None:
      export, props = False, export_or_props
    else:
      export = export_or_props

    container = self.exported_props if export else self.props
    for key, value in props.items():
      append = False
      write_to_exported = False
      while key.startswith('+') or key.startswith('!'):
        if key[0] == '+': append = True
        elif key[0] == '!': write_to_exported = True
        key = key[1:]

      write_target = self.exported_props if write_to_exported else container
      try:
        if append:
          write_target[key] += value
        else:
          write_target[key] = value
      except proplib.NoSuchProperty as exc:
        if on_unknown_property == 'report':
          filename = sys._getframe(1).f_code.co_filename
          lineno = sys._getframe(1).f_lineno
          loc = Cursor(-1, lineno, 0)
          self.context.report_property_does_not_exist(filename, loc, key, write_target.propset)
        else:
          raise


class DslDependency(core.Dependency):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._scope = {'dependency': self}

  @property
  def scope(self):
    return ChainDict(self._scope, self.target.scope)


class Context(core.Context):

  module_class = DslModule
  target_class = DslTarget
  dependency_class = DslDependency

  def __init__(self, build_variant, build_directory, load_builtins=True):
    super().__init__()
    self.module_links_dir = path.join(build_directory, '.module-links')

    self.loader = CraftrModuleLoader(self)
    self.nodepy_context = nodepy.context.Context(parent=require.context)
    self.nodepy_context.resolver.loaders.append(self.loader)
    self.nodepy_context.resolver.paths.append(STDLIB_DIR)
    self.nodepy_context.resolver.paths.append(pathlib.Path(self.module_links_dir))

    # TODO:  Use the nearest available .nodepy/modules directory?
    self.nodepy_context.resolver.paths.append(pathlib.Path(require.context.modules_directory))

    self.build_variant = build_variant
    self.build_directory = build_directory
    self.options = {}
    self.builtins = {'context': self}
    self.require = self.nodepy_context.require

    if load_builtins:
      module = self.require('craftr', exports=False)
      assert module.context is self.nodepy_context
      module = module.namespace
      for key in module.__builtins__:
        self.builtins[key] = getattr(module, key)

    # Remove the build directories module links directory.
    if path.isdir(self.module_links_dir):
      shutil.rmtree(self.module_links_dir)

  def load_module(self, name):
    mod = self.require(name + '.craftr', exports=False)
    return mod.craftr_module

  def load_module_from_file(self, filename, raw=False):
    filename = pathlib.Path(path.canonical(filename))
    module = self.loader.load_module(self.nodepy_context, None, filename)
    self.nodepy_context.register_module(module)
    self.nodepy_context.load_module(module)
    if not raw:
      module = module.craftr_module
    return module

  def link_module(self, parent_dir, module_path):
    """
    This method is called when a `link_module` statement is used in a Craftr
    build script in order to establish a temporary link for the current build
    session to that module.

    This writes a `.nodepy-link` file to the build directories `.module-links`
    directory which is then scanned on imports by Node.py. Every time the
    build system is reconfigured, the `.module-links` directory is flushed.
    """

    do_link(path.canonical(module_path, parent_dir), module_dir=self.module_links_dir)

  def report_property_does_not_exist(self, filename, loc, prop_name, propset):
    print('warn: {}:{}:{}: property {} does not exist'.format(
      filename, loc.lineno, loc.colno, prop_name))

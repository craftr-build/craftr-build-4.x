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

from nr.datastructures.mappings import ChainDict, MappingFromObject

import nodepy
import {CraftrModuleLoader} from './nodepy_glue'
import core from '../core'

STDLIB_DIR = module.package.directory.joinpath('craftr', 'lib')


class DslModule(core.Module):

  nodepy_module = None

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
    self.loader = CraftrModuleLoader(self)
    self.nodepy_context = nodepy.context.Context(parent=require.context)
    self.nodepy_context.resolver.loaders.append(self.loader)
    self.nodepy_context.resolver.paths.append(STDLIB_DIR)

    self.build_variant = build_variant
    self.build_directory = build_directory
    self.options = {}
    self.builtins = {'context': self}
    self.require = self.nodepy_context.require

    if load_builtins:
      module = self.require('craftr.craftr', exports=False)
      assert module.context is self.nodepy_context
      module = module.namespace
      for key in module.__builtins__:
        self.builtins[key] = getattr(module, key)

  def load_module(self, name):
    mod = self.require(name + '.craftr', exports=False)
    return mod.craftr_module

  def load_module_from_file(self, filename, raw=False):
    module = self.loader.load_module(self.nodepy_context, None, filename)
    self.nodepy_context.register_module(module)
    self.nodepy_context.load_module(module)
    if not raw:
      module = module.craftr_module
    return module

  def report_property_does_not_exist(self, filename, loc, prop_name, propset):
    print('warn: {}:{}:{}: property {} does not exist'.format(
      filename, loc.lineno, loc.colno, prop_name))

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
This module implements the glue between Node.py and Craftr build scripts.
"""

from nodepy.utils import pathlib
from nr.datastructures.mappings import ChainDict, ObjectFromMapping

import nodepy
import {Parser} from './parser'
import {Interpreter} from './interpreter'


class CraftrModule(nodepy.loader.PythonModule):
  """
  Subclass of the Node.py #PythonModule that represents a Craftr build module.
  It uses #@craftr/craftr-build/dsl to parse and evaluate the build script.

  # Parameters
  dsl_context (@craftr/craftr-build/dsl/interpreter:Context): The Craftr
    DSL context that implements the evaluation behaviour.
  *args, **kwargs: Passed on to the #PythonModule constructor.

  # Members
  craftr_module (@craftr/craftr-build/core:Module): The Craftr core module
    object that contains all properties and targets.
  """

  def __init__(self, dsl_context, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.dsl_context = dsl_context
    self.craftr_module = None
    self._members = {}

  def create_namespace(self):
    return ObjectFromMapping(ChainDict(self._members, self.dsl_context.builtins), self.name)

  def _preprocess_code(self, code):
    return code

  def __setattr__(self, key, value):
    super().__setattr__(key, value)

  def _exec_code(self, code):
    assert self.loaded
    is_main = False
    code = code.replace('\r\n', '\n')
    project = Parser().parse(code, str(self.filename))
    if project.name in self.dsl_context.modules:
      raise RuntimeError('modules {!r} already loaded'.format(project.name))
    interpreter = Interpreter(self, self.dsl_context, str(self.filename), is_main)
    self.craftr_module = interpreter.create_module(project)
    self.namespace.module = self.craftr_module
    interpreter.eval_module(project, self.craftr_module)
    assert self.loaded
    self.dsl_context.modules[self.craftr_module.name] = self.craftr_module

  def preprocess_eval_block(self, code):
    return super()._preprocess_code(code)

  def init(self):
    super().init()
    self.namespace.module = self.craftr_module


class CraftrModuleLoader(nodepy.resolver.StdResolver.Loader):
  """
  A loader implementation that can load Craftr build modules. The load request
  must include the `.craftr` suffix of the build module files.
  """

  def __init__(self, dsl_context):
    self.dsl_context = dsl_context

  def suggest_files(self, nodepy_context, path):
    if path.suffix == '.craftr':
      yield path
      yield path.with_suffix('').joinpath('build.craftr')

  def can_load(self, nodepy_context, path):
    return path.suffix == '.craftr'

  def load_module(self, context, package, filename):
    return CraftrModule(self.dsl_context, context, None, pathlib.Path(filename))

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

from nr import path
from nr.ast.dynamic_eval import dynamic_exec, dynamic_eval
from nodepy.utils.path import pathlib

import nodepy
import * from './parser'

__all__ = ['RunError', 'OptionError', 'MissingRequiredOptionError',
           'InvalidOptionError', 'InvalidAssignmentError', 'ModuleNotFoundError',
           'ExplicitRunError', 'Interpreter']


class RunError(Exception):
  pass


class OptionError(RunError):

  def __init__(self, module_name, option_name, message=None):
    self.module_name = module_name
    self.option_name = option_name
    self.message = message

  def __str__(self):
    result = '{}.{}'.format(self.module_name, self.option_name)
    if self.message:
      result += ': ' + str(self.message)
    return result


class MissingRequiredOptionError(OptionError):
  pass


class InvalidOptionError(OptionError):
  pass


class InvalidAssignmentError(RunError):

  def __init__(self, propset, loc, message):
    self.propset = propset
    self.loc = loc
    self.message = message

  def __str__(self):
    return '{} ({}:{}): {}'.format(self.propset, self.loc.lineno,
      self.loc.colno, self.message)


class ModuleNotFoundError(RunError):
  pass


class ExplicitRunError(RunError):
  pass


class Interpreter:
  """
  Interpreter for projects.
  """

  def __init__(self, nodepy_module, context, filename, is_main=False):
    self.nodepy_module = nodepy_module
    self.context = context
    self.filename = filename
    self.directory = path.dir(filename)
    self.is_main = is_main

  def __call__(self, namespace):
    module = self.create_module(namespace)
    self.eval_module(namespace, module)
    return module

  def create_module(self, namespace):
    if not self.nodepy_module.loaded:
      self.nodepy_module.init()
    module = self.context.module_class(
      self.context, namespace.name, namespace.version, self.directory)
    module.nodepy_module = self.nodepy_module
    return module

  def eval_module(self, namespace, module):
    for node in namespace.children:
      if isinstance(node, Eval):
        self._eval_block(node, module)
      elif isinstance(node, Options):
        self._options(node, module)
      elif isinstance(node, Pool):
        module.add_pool(node.name, node.depth)
      elif isinstance(node, Target):
        self._target(node, module)
      elif isinstance(node, Assignment):
        self._assignment(node, module)
      elif isinstance(node, Export):
        self._export_block(node, module)
      elif isinstance(node, Configure):
        if self.is_main:
          self.context.options.update(node.data)
      elif isinstance(node, LinkModule):
        self.context.link_module(module.directory, node.path)
      else:
        assert False, node

  def _options(self, node, module):
    assert module is self.nodepy_module.craftr_module, (module, self.nodepy_module.craftr_module)
    options = module.options
    for key, (type, value, loc) in node.options.items():
      option_name = module.name + ':' + key
      try:
        has_value = self.context.options[option_name]
      except KeyError:
        if value is None:
          raise MissingRequiredOptionError(module.name, option_name)
        has_value = self._eval(loc.lineno, value, module.scope)
      try:
        has_value = Options.adapt(type, has_value)
      except ValueError as exc:
        raise InvalidOptionError(module.name, key, str(exc))
      setattr(options, key, has_value)

  def _exec(self, lineno, source, vars):
    source = '\n' * (lineno-1) + source
    source = self.nodepy_module.preprocess_eval_block(source)
    dynamic_exec(source, vars, filename=self.filename)

  def _eval(self, lineno, source, vars):
    source = '\n' * (lineno-1) + source
    return dynamic_eval(source, vars, filename=self.filename)

  def _assignment(self, node, obj, override_export=False):
    assert isinstance(obj, (core.Module, core.Target, core.Dependency)), type(obj)
    export = override_export or node.export

    if isinstance(obj, core.Target):
      props = obj.exported_props if export else obj.props
    else:
      if export:
        raise RuntimeError('can not export properties in a non-target context')
      props = obj.props

    propname = node.scope + '.' + node.propname
    if propname not in props:
      self.context.report_property_does_not_exist(self.filename, node.loc, propname, obj)
      return

    value = self._eval(node.loc.lineno, node.expression, obj.scope)
    try:
      props[propname] = value
    except (TypeError, ValueError) as exc:
      # TODO: Make it appear as if the exception was raised in the
      #       assignment expression.
      raise InvalidAssignmentError(obj, node.loc, str(exc))

  def _target(self, node, module):
    if not self._test_if_expr(node, module):
      return
    target = module.add_target_with_class(
      self.context.target_class, node.name, node.public)
    for node in node.children:
      if isinstance(node, Eval):
        self._eval_block(node, target)
      elif isinstance(node, Assignment):
        self._assignment(node, target)
      elif isinstance(node, Dependency):
        self._dependency(node, target)
      elif isinstance(node, Export):
        self._export_block(node, target)
      else:
        assert False, node

  def _dependency(self, node, parent_target, override_export=False):
    if not self._test_if_expr(node, parent_target):
      return
    if node.name.startswith('@'):
      sources = [parent_target.module.targets[node.name[1:]]]
      module = parent_target.module
    elif '@' in node.name:
      module_name, target_name = node.name.partition('@')[::2]
      module = parent_target.module.load_module(module_name)
      sources = [module.targets[target_name]]
    else:
      module = parent_target.module.load_module(node.name)
      sources = [x for x in module.targets.values() if x.public]
    dep = parent_target.add_dependency_with_class(
      self.context.dependency_class, sources, override_export or node.export)
    for assign in node.assignments:
      assert isinstance(assign, Assignment), assign
      self._assignment(assign, dep)
    if node.assign_to:
      parent_target.scope[node.assign_to] = module.nodepy_module.namespace

  def _export_block(self, node, obj):
    assert isinstance(obj, core.Target)
    if not self._test_if_expr(node, obj):
      return
    for child in node.assignments:
      if isinstance(child, Assignment):
        self._assignment(child, obj, override_export=True)
      elif isinstance(child, Dependency):
        self._dependency(child, obj, override_export=True)
      else:
        assert False, child

  def _eval_block(self, node, obj):
    if not self._test_if_expr(node, obj):
      return
    self._exec(node.loc.lineno, node.source, obj.scope)

  def _test_if_expr(self, node, obj):
    if node.if_expr:
      return bool(self._eval(node.loc.lineno, node.if_expr, obj.scope))
    return True

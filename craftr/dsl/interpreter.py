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
from nr.datastructures.chaindict import ChainDict
from nr.datastructures.objectfrommapping import ObjectFromMapping
from nr.ast.dynamic_eval import dynamic_exec, dynamic_eval
from nodepy.utils.path import pathlib

import nodepy

import * from './parser'
import core from '../core'

__all__ = ['RunError', 'OptionError', 'MissingRequiredOptionError',
           'InvalidOptionError', 'InvalidAssignmentError', 'ModuleNotFoundError',
           'ExplicitRunError', 'Context', 'Interpreter']


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


class ModuleOptions:

  def __init__(self, name):
    self._name = name
    self._data = {}

  def __repr__(self):
    return 'ModuleOptions({!r}, {!r})'.format(self._name, self._data)

  def __getattr__(self, key):
    try:
      return self._data[key]
    except KeyError:
      raise AttributeError(key)

  def __setattr__(self, key, value):
    if key not in ('_name', '_data'):
      self._data[key] = value
    else:
      super().__setattr__(key, value)


class CraftrNodepyModule(nodepy.loader.PythonModule):

  def __init__(self, dsl_context, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.dsl_context = dsl_context
    self.craftr_module = None

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
    self.craftr_module = interpreter(project)
    assert self.loaded
    self.dsl_context.modules[self.craftr_module.name] = self.craftr_module

  def preprocess_eval_block(self, code):
    return super()._preprocess_code(code)


class CraftrNodepyScript(nodepy.loader.PythonModule):

  def __init__(self, scope, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.scope = scope

  def _exec_code(self, code):
    dynamic_exec(code, self.scope, filename=str(self.filename))

  def init(self):
    super().init()
    old_namespace, self.namespace = self.namespace, ObjectFromMapping(self.scope)
    for key in ['__name__', '__file__', 'require']:
      setattr(self.namespace, key, getattr(old_namespace, key))


class Context(core.Context):
  """
  An extension of the #core.Context interface that implements the basic
  behaviour of the context with the Craftr DSL.
  """

  class ModuleLoader(nodepy.resolver.StdResolver.Loader):

    def __init__(self, dsl_context):
      self.dsl_context = dsl_context

    def suggest_files(self, nodepy_context, path):
      if path.suffix == '.craftr':
        yield path
        yield path.with_suffix('').joinpath('build.craftr')

    def can_load(self, nodepy_context, path):
      return path.suffix == '.craftr'

    def load_module(self, context, package, filename):
      return CraftrNodepyModule(self.dsl_context, require.context, None, pathlib.Path(filename))

  def __init__(self, build_variant, build_directory):
    super().__init__()
    self.build_variant = build_variant
    self.build_directory = build_directory
    self.options = {}
    self.modules = {}
    self.loader = self.ModuleLoader(self)

    # TODO: Remove again after
    craftr_dir = path.dir(path.dir(__file__))
    require.context.resolver.loaders.append(self.loader)
    require.context.resolver.paths.append(pathlib.Path(craftr_dir).joinpath('lib'))
    print(require.context.resolver.paths)

    self._builtins = {}
    craftr = self.load_module('craftr')
    for key in craftr.__builtins__:
      self._builtins[key] = getattr(craftr, key)

  def get_builtins(self):
    return self._builtins

  def load_module(self, name, get_nodepy_module=False):
    return require(name + '.craftr', exports=not get_nodepy_module)

  def load_file(self, filename, is_main=False, get_nodepy_module=False):
    return require(path.abs(filename), exports=not get_nodepy_module)

  def load_script(self, filename, context):
    assert hasattr(context, '__getitem__'), context
    nodepy_module = CraftrNodepyScript(context, require.context, None, pathlib.Path(filename))
    nodepy_module.init()
    nodepy_module.load()
    return context

  def report_property_does_not_exist(self, filename, loc, prop_name, propset):
    print('warn: {}:{}:{}: property {} does not exist'.format(
      filename, loc.lineno, loc.colno, prop_name))

  def get_exec_vars(self, obj):
    assert isinstance(obj, (core.Module, core.Target, core.Dependency)), obj
    if not hasattr(obj, 'scope'):
      if isinstance(obj, core.Module):
        obj.scope = vars(obj.nodepy_module.namespace)
      else:
        obj.scope = {}
    if isinstance(obj, core.Module):
      obj.scope['context'] = self
      obj.scope['module'] = obj
      obj.scope['self'] = obj
      return ChainDict(obj.scope, self.get_builtins())
    elif isinstance(obj, core.Target):
      obj.scope['self'] = obj
      obj.scope['target'] = obj
      return ChainDict(obj.scope, self.get_exec_vars(obj.module))
    else:
      obj.scope['self'] = obj
      return ChainDict(obj.scope, self.get_exec_vars(obj.target))

  def init_module(self, module):
    pass

  def init_target(self, target):
    pass

  def init_dependency(self, dep):
    pass

  def finalize_module(self, module):
    pass

  def finalize_target(self, target):
    pass

  def finalize_dependency(self, dependency):
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
    module = core.Module(self.context, namespace.name, namespace.version, self.directory)
    module.nodepy_module = self.nodepy_module
    self.context.init_module(module)
    return module

  def eval_module(self, namespace, module):
    for node in namespace.children:
      if isinstance(node, Eval):
        self._exec(node.loc.lineno, node.source, self.context.get_exec_vars(module))
      elif isinstance(node, Load):
        self._load(node.loc.lineno, node.filename, self.context.get_exec_vars(module))
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
      elif isinstance(node, Using):
        self.context.load_module(node.name)
      else:
        assert False, node
    self.context.finalize_module(module)

  def _options(self, node, module):
    scope = self.context.get_exec_vars(module)
    options = scope.setdefault('options', ModuleOptions(module.name))
    for key, (type, value, loc) in node.options.items():
      option_name = module.name + '.' + key
      try:
        has_value = self.context.options[option_name]
      except KeyError:
        if value is None:
          raise MissingRequiredOptionError(module.name, option_name)
        has_value = self._eval(loc.lineno, value, self.context.get_exec_vars(module))
      try:
        has_value = Options.adapt(type, has_value)
      except ValueError as exc:
        raise InvalidOptionError(module.name, key, str(exc))
      setattr(options, key, has_value)

  def _load(self, lineno, filename, namespace):
    if not path.isabs(filename):
      filename = path.join(self.directory, filename)
    filename = path.norm(filename)
    with override_member(namespace, '__file__', filename):
      self.context.load_script(filename, namespace)

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

    value = self._eval(node.loc.lineno, node.expression, self.context.get_exec_vars(obj))
    try:
      props[propname] = value
    except (TypeError, ValueError) as exc:
      # TODO: Make it appear as if the exception was raised in the
      #       assignment expression.
      raise InvalidAssignmentError(obj, node.loc, str(exc))

  def _target(self, node, module):
    target = module.add_target(node.name, node.public)
    self.context.init_target(target)
    for node in node.children:
      if isinstance(node, Eval):
        self._exec(node.loc.lineno, node.source, self.context.get_exec_vars(target))
      elif isinstance(node, Assignment):
        self._assignment(node, target)
      elif isinstance(node, Dependency):
        self._dependency(node, target)
      elif isinstance(node, Export):
        self._export_block(node, target)
      else:
        assert False, node
    self.context.finalize_target(target)

  def _dependency(self, node, parent_target):
    if node.name.startswith('@'):
      sources = [parent_target.module.targets[node.name[1:]]]
    else:
      module = self.context.load_module(node.name)
      sources = [x for x in module.targets.values() if x.public]
    dep = parent_target.add_dependency(sources, node.export)
    self.context.init_dependency(dep)
    for assign in node.assignments:
      assert isinstance(assign, Assignment), assign
      self._assignment(assign, dep)
    self.context.finalize_dependency(dep)

  def _export_block(self, node, obj):
    assert isinstance(obj, core.Target)
    for assign in node.assignments:
      self._assignment(assign, obj, override_export=True)

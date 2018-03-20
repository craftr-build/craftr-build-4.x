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

from .. import core
from .parser import *

from nr import path
from nr.datastructures.chaindict import ChainDict
from nr.ast.dynamic_eval import dynamic_exec, dynamic_eval

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


class Context(core.Context):
  """
  An extension of the #core.Context interface that implements the basic
  behaviour of the context with the Craftr DSL.
  """

  def __init__(self, build_variant, build_directory):
    super().__init__()
    self.build_variant = build_variant
    self.build_directory = build_directory
    self.options = {}
    self.modules = {}
    craftr_dir = path.dir(path.dir(__file__))
    self.path = ['.', path.join(craftr_dir, 'lib')]
    self._builtins = self.load_script(path.join(craftr_dir, 'lib', 'builtins.py'), {'context': self})

  def get_builtins(self):
    return self._builtins

  def load_module(self, name):
    if name not in self.modules:
      for x in self.path:
        filename = path.join(x, name + '.craftr')
        if path.isfile(filename):
          break
        filename = path.join(x, name, 'build.craftr')
        if path.isfile(filename):
          break
      else:
        raise ModuleNotFoundError(name)
      with open(filename) as fp:
        project = Parser().parse(fp.read(), filename)
      module = Interpreter(self, filename)(project)
      self.modules[name] = module
    else:
      module = self.modules[name]
    return module

  def load_file(self, filename, is_main=False):
    with open(filename) as fp:
      project = Parser().parse(fp.read(), filename)
    if project.name in self.modules:
      raise RuntimeError('modules {!r} already loaded'.format(project.name))
    module = Interpreter(self, filename, is_main)(project)
    self.modules[module.name] = module
    return module

  def load_script(self, filename, context):
    assert hasattr(context, '__getitem__'), context
    with open(filename) as fp:
      dynamic_exec(fp.read(), context, filename=filename)
    return context

  def report_property_does_not_exist(self, filename, loc, prop_name, propset):
    print('warn: {}:{}:{}: property {} does not exist'.format(
      filename, loc.lineno, loc.colno, prop_name))

  def get_exec_vars(self, obj):
    assert isinstance(obj, (core.Module, core.Target, core.Dependency)), obj
    if not hasattr(obj, 'scope'):
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

  def __init__(self, context, filename, is_main=False):
    self.context = context
    self.filename = filename
    self.directory = path.dir(filename)
    self.is_main = is_main

  def __call__(self, namespace):
    module = self.create_module(namespace)
    self.eval_module(namespace, module)
    return module

  def create_module(self, namespace):
    module = core.Module(self.context, namespace.name, namespace.version, self.directory)
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
          raise MissingRequiredOptionError(option_name)
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
    dynamic_exec(source, vars, filename=self.filename)

  def _eval(self, lineno, source, vars):
    source = '\n' * (lineno-1) + source
    return dynamic_eval(source, vars, filename=self.filename)

  def _assignment(self, node, obj, override_export=False):
    assert isinstance(obj, (core.Module, core.Target, core.Dependency)), type(obj)
    export = override_export or node.export
    if export and not isinstance(obj, core.Target):
      raise RuntimeError('can not export properties in a non-target context')
    props = obj.exported_props if export else obj.props
    propname = node.scope + '.' + node.propname
    if propname not in props:
      self.context.report_property_does_not_exist(self.filename, node.loc, name, obj)
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
    dep = parent_target.add_dependency(sources, node.public)
    self.context.init_dependency(dep)
    for assign in node.assignments:
      assert isinstance(assign, Assignment), assign
      self._assignment(assign, dep)
    self.context.finalize_dependency(dep)

  def _export_block(self, node, propset):
    assert propset.supports_exported_members(), propset
    for assign in node.assignments:
      self._assignment(assign, propset, override_export=True)

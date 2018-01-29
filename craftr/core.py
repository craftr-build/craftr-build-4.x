
import collections
import os
import re

from .props import PropertySet


def validate_module_name(name):
  if not re.match('^[\w\d_\-/]+$', name):
    raise ValueError('invalid module name: {!r}'.format(name))


def validate_target_name(name):
  if not re.match('^[\w\d_\-]+$', name):
    raise ValueError('invalid target name: {!r}'.format(name))


class Options(PropertySet):
  """
  Represents options.
  """

  def __repr__(self):
    return 'Options()'


class Module(PropertySet):
  """
  Represents a module.
  """

  def __init__(self, name, version, directory):
    super().__init__()
    validate_module_name(name)
    self._name = name
    self._version = version
    self._directory = directory
    self._targets = {}
    self._options = Options()
    self._target_handlers = []

  def __repr__(self):
    return 'Module({!r} v{})'.format(self._name, self._version)

  def name(self):
    return self._name

  def version(self):
    return self._version

  def targets(self, exported_only=False):
    for target in self._targets.values():
      if not exported_only or target.is_exported():
        yield target

  def target(self, name):
    if name not in self._targets:
      # TODO: A separate exception type
      raise RuntimeError('target {!r} does not exist'.format(self._name + ':' + name))
    return self._targets[name]

  def add_target(self, name, export=False, directory=None):
    target = Target(self, name, export, directory or self._directory)
    if target.name in self._targets:
      raise RuntimeError('target already defined: {!r}'.format(self._name + ':' + target.name))
    for handler in self.target_handlers():
      handler.setup_target(target)
    self._targets[target.name] = target
    return target

  def register_target_handler(self, handler):
    if not isinstance(handler, TargetHandler):
      raise TypeError('expected TargetHandler')
    self._target_handlers.append(handler)

  def target_handlers(self):
    return iter(self._target_handlers)


class Target(PropertySet):
  """
  Represents a target. A target is added to a project using the `target` block.
  """

  TaggedFile = collections.namedtuple('TaggedFile', 'name tag')

  def __init__(self, module, name, export, directory):
    super().__init__(True)
    validate_target_name(name)
    self._module = module
    self._name = name
    self._export = export
    self._directory = directory
    self._dependencies = []
    self._outputs = []
    self.define_property('this.pool', 'String', None)
    self.define_property('this.syncio', 'Bool', False)
    self.define_property('this.explicit', 'Bool', False)
    self.define_property('this.directory', 'String', None)

  def __repr__(self):
    return 'Target({!r} of {})'.format(self._name, self._module)

  def module(self):
    return self._module

  def name(self):
    return self._name

  def is_exported(self):
    return self._export

  def dependencies(self, exported_only=False):
    for dep in self._dependencies:
      if not exported_only or dep.is_exported():
        yield dep

  def transitive_dependencies(self):
    """
    Returns a generator for all direct and indirect dependencies.
    """

    seen = set()
    def transitive_deps(dep):
      for target in dep.targets():
        for dep in target._dependencies:
          if dep.is_exported() and dep not in seen:
            yield dep
            seen.add(dep)
            yield from transitive_deps(dep)
    for dep in self._dependencies:
      if dep not in seen:
        yield dep
        seen.add(dep)
        yield from transitive_deps(dep)

  def add_dependency(self, obj, export=False):
    if isinstance(obj, Module):
      module, target = obj, None
    elif isinstance(obj, Target):
      module, target = None, obj
    else:
      raise TypeError('expected Module or Target object')
    dep = Dependency(module, target, export)
    for handler in self.target_handlers():
      handler.setup_dependency(dep)
    if module:
      for handler in module.target_handlers():
        handler.setup_dependency(dep)
        handler.setup_target(self)
    self._dependencies.append(dep)
    return dep

  def directory(self):
    result = self.get_property('this.directory', None)
    if result is not None and not os.path.isabs(result):
      result = os.path.join(self._directory, result)
    elif result is None:
      result = self._directory
    return result

  def target_handlers(self):
    seen = set()
    for handler in self._module.target_handlers():
      if handler not in seen:
        yield handler
        seen.add(handler)
    for dep in self._dependencies:
      for handler in dep.module().target_handlers():
        if handler not in seen:
          yield handler
          seen.add(handler)

  def outputs(self, tag=None):
    if tag is not None:
      return (x.name for x in self._outputs if x.tag == tag)
    else:
      return iter(self._outputs)

  def add_outputs(self, tag, outputs):
    if not isinstance(outputs, list):
      raise TypeError('expected list for outputs')
    if not isinstance(tag, str):
      raise TypeError('expected str for tag')
    self._outputs += [self.TaggedFile(tag, name) for name in outputs]

  def _inherited_propsets(self):
    for dep in self.transitive_dependencies():
      yield from dep.targets()


class Dependency(PropertySet):
  """
  Represents a dependency. A dependency is added to a target using a
  `requires` statement or block.
  """

  def __init__(self, module=None, target=None, export=False):
    super().__init__()
    if bool(module) == bool(target):
      raise ValueError('either module OR target must be specified')
    if module and not isinstance(module, Module):
      raise TypeError('module must be Module object')
    if target and not isinstance(target, Target):
      raise TypeError('target must be Target object')
    self._module = module
    self._target = target
    self._export = export
    self.define_property('this.select', 'StringList', [])

  def __repr__(self):
    s = ("@"+ self._target.name()) if self._target else self._module.name()
    return 'Dependency({!r})'.format(s)

  def module(self):
    if self._target:
      return self._target.module()
    return self._module

  def target(self):
    return self._target

  def is_exported(self):
    return self._export

  def targets(self):
    if self._target:
      yield self._target
    else:
      select = self.get_property('this.select', inherit=False)
      if not select:
        yield from self._module.targets(exported_only=True)
      else:
        for name in select:
          yield self._module.target(name)


class TargetHandler:
  """
  Interface for implementing target handlers. A target handler is responsible
  for defining new properties on a target and then in the translation step
  create build actions based on these properties.
  """

  def setup_target(self, target):
    pass

  def setup_dependency(self, target):
    pass

  # TODO: Translation step

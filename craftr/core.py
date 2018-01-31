
import collections
import os
import re
import sys

from . import path, props


def validate_module_name(name):
  if not re.match('^[\w\d_\-/]+$', name):
    raise ValueError('invalid module name: {!r}'.format(name))


def validate_target_name(name):
  if not re.match('^[\w\d_\-]+$', name):
    raise ValueError('invalid target name: {!r}'.format(name))


Pool = collections.namedtuple('Pool', 'name depth')


class TaggedFile:
  """
  Represents a file attached with zero or more tags.

  This class interns all tag strings.
  """

  def __init__(self, name, tags=()):
    self._name = path.canonical(name)
    self._tags = set(sys.intern(x) for x in tags)

  def __repr__(self):
    return 'TaggedFile(name={!r}, tags={{{!r}}})'.format(self.name, ','.join(self.tags))

  def has_tag(self, tag):
    return tag in self._tags

  def add_tags(self, tags):
    self._tags |= set(sys.intern(x) for x in tags)

  @property
  def name(self):
    return self._name

  @property
  def tags(self):
    return set(self._tags)


class Options(props.PropertySet):
  """
  Represents options.
  """

  def __repr__(self):
    return 'Options()'


class Module(props.PropertySet):
  """
  Represents a module.
  """

  def __init__(self, name, version, directory):
    super().__init__()
    validate_module_name(name)
    self._name = name
    self._version = version
    self._directory = directory
    self._targets = collections.OrderedDict()
    self._pools = collections.OrderedDict()
    self._options = Options()
    self._target_handlers = []
    self._eval_namespace = props.Namespace('module "{}"'.format(name))
    self._eval_namespace.module = self

  def __repr__(self):
    return 'Module({!r} v{})'.format(self._name, self._version)

  def name(self):
    return self._name

  def version(self):
    return self._version

  def directory(self):
    return self._directory

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
    self._targets[target.name()] = target
    return target

  def add_pool(self, name, depth):
    self._pools[name] = Pool(name, depth)

  def pool(self, name):
    return self._pools[name]

  def register_target_handler(self, handler):
    if not isinstance(handler, TargetHandler):
      raise TypeError('expected TargetHandler')
    self._target_handlers.append(handler)

  def target_handlers(self):
    return iter(self._target_handlers)

  def eval_namespace(self):
    return self._eval_namespace


class Target(props.PropertySet):
  """
  Represents a target. A target is added to a project using the `target` block.
  """

  def __init__(self, module, name, export, directory):
    super().__init__(True)
    validate_target_name(name)
    self._module = module
    self._name = name
    self._export = export
    self._directory = directory
    self._dependencies = []
    self._outputs = {}
    self._handler_data = {}
    self._eval_namespace = props.duplicate_namespace(
      module.eval_namespace(), 'target "{}"'.format(name))
    self._eval_namespace.target = self
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
    dep = Dependency(self, module, target, export)
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
      return filter(TaggedFile.has_tag, self._outputs.values())
    else:
      return self._outputs.values()

  def add_output(self, name, tags=()):
    name = path.canonical(name)
    # We build the hash table using the case-insensitive canonical name.
    name_lower = name.lower()
    obj = self._outputs.get(name_lower)
    if obj is None:
      obj = TaggedFile(name, tags)
    else:
      obj.add_tags(tags)
    return obj

  def get_output(self, name):
    name = path.canonical(name)
    return self._outputs.get(name.lower())

  def eval_namespace(self):
    return self._eval_namespace

  def finalize(self):
    for handler in self.target_handlers():
      common_scope = handler.get_common_property_scope()
      data = self.get_properties(common_scope) if common_scope else props.Namespace()
      handler_data = handler.finalize_target(self, data) or data
      self._handler_data[handler] = handler_data

  def handler_data(self, handler):
    return self._handler_data.get(handler)

  # props.PropertySet overrides

  def _inherited_propsets(self):
    for dep in self.transitive_dependencies():
      yield from dep.targets()

  def _on_new_namespace(self, scope, ns):
    setattr(self._eval_namespace, scope, ns)


class Dependency(props.PropertySet):
  """
  Represents a dependency. A dependency is added to a target using a
  `requires` statement or block.
  """

  def __init__(self, parent, module=None, target=None, export=False):
    super().__init__()
    if bool(module) == bool(target):
      raise ValueError('either module OR target must be specified')
    if module and not isinstance(module, Module):
      raise TypeError('module must be Module object')
    if target and not isinstance(target, Target):
      raise TypeError('target must be Target object')
    self._parent = parent
    self._module = module
    self._target = target
    self._export = export
    self._eval_namespace = props.duplicate_namespace(
      parent.eval_namespace(), 'dependency "{}"'.format(self._refstring()))
    self.define_property('this.select', 'StringList', [])

  def __repr__(self):
    return 'Dependency({} of {})'.format(self._refstring(), self._parent)

  def _refstring(self):
    return ("@"+ self._target.name()) if self._target else self._module.name()

  def parent(self):
    return self._parent

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

  def eval_namespace(self):
    return self._eval_namespace

  def finalize(self):
    for handler in self._parent.target_handlers():
      common_scope = handler.get_common_property_scope()
      data = self.get_properties(common_scope) if common_scope else props.Namespace()
      handler.finalize_dependency(self, data)


class TargetHandler:
  """
  Interface for implementing target handlers. A target handler is responsible
  for defining new properties on a target and then in the translation step
  create build actions based on these properties.
  """

  def get_common_property_scope(self):
    """
    If this returns something other than #None, the *data* argument to the
    #finalize_target() and #finalize_dependency() methods will be filled
    with the property values of this scope.
    """

    return None

  def setup_target(self, target):
    pass

  def setup_dependency(self, dependency):
    pass

  def finalize_target(self, target, data):
    """
    Called after the target has been created and fully initialized by the
    DSL interpreter. This method is supposed to add output files to the
    target that may need to be considered by other targets that depend
    on this one.

    During the process, information may be retrieved that would also be
    needed in #translate_target(). This information can be filled into the
    *data* #props.Namespace object, or into a custom object that needs to
    be returned.

    If #get_common_property_scope() is implemented, the #props.Namespace
    *data* object will be filled with the scope's property values.
    """

    pass

  def finalize_dependency(self, dependency, data):
    pass

  def translate_target(self, target, data):
    """
    Called after a build script has been loaded to translate the target into
    concrete build actions. The *data* parameter is the value returned by
    the #finalize_target() method.
    """

    pass

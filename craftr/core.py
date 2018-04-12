# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
"""
The core module in Craftr implements targets and their properties independent
from the aspect of Craftr DSL.
"""

from nr.stream import stream
from nr.datastructures.mappings import ObjectFromMapping

import collections
import warnings

import {Action, BuildGraph, FileSet} from './build'
import proplib from './proplib'


class Context:
  """
  The context contains global information for the build system.
  """

  def __init__(self):
    self.module_properties = proplib.PropertySet(allow_any=True)
    Module.setup_standard_properties(self.module_properties)
    self.target_properties = proplib.PropertySet()
    Target.setup_standard_properties(self.target_properties)
    self.dependency_properties = proplib.PropertySet()
    Dependency.setup_standard_properties(self.dependency_properties)
    self.handlers = []
    self.modules = []
    self.graph = BuildGraph()

  def register_handler(self, handler):
    handler.init(self)
    self.handlers.append(handler)

  def iter_targets(self):
    """
    Iterates over all targets in the context in post-order.
    """

    seen = set()

    def recurse_target(target):
      for dep in target.transitive_dependencies().attr('sources').concat():
        if dep not in seen:
          seen.add(dep)
          yield dep
          yield from recurse_layers(dep)
          yield from recurse_target(dep)

    def recurse_layers(target):
      for layer in target.iter_layers():
        if layer not in seen:
          seen.add(layer)
          yield from recurse_target(layer)
          yield layer

    for module in self.modules:
      for target in module.targets.values():
        yield from recurse_target(target)
        yield target
        yield from recurse_layers(target)

  def iter_targets_additive(self):
    """
    Iterates over all targets in the context in post-order, until no more new
    targets are created.
    """

    seen = set()
    has_new_targets = True
    while has_new_targets:
      has_new_targets = False
      for target in self.iter_targets():
        if target not in seen:
          seen.add(target)
          yield target
          has_new_targets = True

  def translate_targets(self):
    """
    Invokes the translation process for all targets in all modules in the
    Context.
    """

    for handler in self.handlers:
      handler.translate_begin()

    for target in self.iter_targets_additive():
      for handler in self.handlers:
        handler.preprocess_target(target)
    for target in self.iter_targets_additive():
      for handler in self.handlers:
        handler.translate_target(target)

    for handler in self.handlers:
      handler.translate_end()

    def add_target_actions(target):
      self.graph.add_actions(target.actions.values())
      for layer in target.iter_layers():
        add_target_actions(layer)

    for module in self.modules:
      for target in module.targets.values():
        add_target_actions(target)


class Module:
  """
  Represents a namespace for targets. Every build script in the Craftr DSL
  has its own namespace, which must be explicitly declared with the `namespace`
  keyword. Additionally, a version number may be declared which can be used
  by target handlers for default filenames, etc. Every namespace is also
  associated with a directory that all paths, if they are not absolute, should
  be treated relative to.
  """

  @staticmethod
  def setup_standard_properties(props):
    pass

  def __init__(self, context, name, version, directory):
    self.context = context
    self.name = name
    self.version = version
    self.directory = directory
    self.targets = collections.OrderedDict()
    self.pools = collections.OrderedDict()
    self.props = proplib.Properties(context.module_properties, self)

  def __repr__(self):
    return 'Module(name={!r}, version={!r}, directory={!r})'.format(
      self.name, self.version, self.directory)

  def add_target_with_class(self, target_cls, name, public=False):
    if name in self.targets:
      raise ValueError('target name {!r} already occupied'.format(name))
    target = target_cls(self, name, public)
    self.targets[target.name] = target
    for handler in self.context.handlers:
      handler.target_created(target)
    return target

  def add_target(self, *args, **kwargs):
    return self.add_target_with_class(Target, *args, **kwargs)

  def add_pool(self, name, depth):
    if name in self.pools:
      raise ValueError('pool {!r} already defined'.format(name))
    self.pools[name] = depth

  def public_targets(self):
    return (x for x in self.targets.values() if x .public)


class Target:
  """
  A target represents a collection of properties and dependencies to other
  targets. Targets will be translated into build actions by target handlers
  based on their properties and dependencies.
  """

  @staticmethod
  def setup_standard_properties(propset):
    propset.add('this.directory', proplib.String)
    propset.add('this.outputDirectory', proplib.String)
    propset.add('this.pool', proplib.String)
    propset.add('this.explicit', proplib.Bool, default=False)
    propset.add('this.syncio', proplib.Bool, default=False)

  def __init__(self, module, name, public, parent=None, redirect_actions=False):
    if parent:
      assert module == parent.module, "differing modules"
    if redirect_actions and not parent:
      raise ValueError('"redirect_actions" can not be True without "parent"')
    self.parent = parent
    self.redirect_actions = redirect_actions
    self.module = module
    self.name = name
    self.public = public
    self.props = proplib.Properties(module.context.target_properties, self)
    self.exported_props = proplib.Properties(module.context.target_properties, self)
    self.dependencies = []
    self.actions = collections.OrderedDict()
    self.layers = {}
    self._layers_list = []  # Can be appended to during iteration.

  def __repr__(self):
    return 'Target(id={!r}, public={!r})'.format(self.id, self.public)

  @property
  def context(self):
    return self.module.context

  @property
  def id(self):
    return '{}@{}'.format(self.module.name, self.full_name)

  @property
  def full_name(self):
    if self.parent:
      return self.parent.full_name + '/' + self.name
    return self.name

  @property
  def directory(self):
    result = self.get_prop('this.directory', default=None)
    if result is None:
      if self.parent:
        result = self.parent.directory
      else:
        result = self.module.directory
    return result

  @property
  def output_actions(self):
    """
    Returns a list for the target's output actions. If there is at least
    one action that is explicitly marked as output, only actions that are
    marked as such will be returned. Otherwise, the last action that was
    created and not explicitly marked as NO output will be returned.
    """

    result = []
    last_default_output = None
    for action in self.actions.values():
      if action.is_output:
        result.append(action)
      elif action.is_output is None:
        last_default_output = action
    if not result and last_default_output:
      result.append(last_default_output)
    return result

  def get_prop(self, prop_name, inherit=False, default=NotImplemented):
    """
    Returns a property value, preferring the value in the #exported_props.

    If *inherit* is #True, the property must be a #proplib.List property
    and the values in the exported and non-exported property containers as
    well as transitive dependencies are respected.
    """

    if inherit:
      def iter_values():
        yield self.exported_props[prop_name]
        yield self.props[prop_name]
        for target in self.transitive_dependencies().attr('sources').concat():
          yield target.exported_props[prop_name]
      prop = self.context.target_properties[prop_name]
      return prop.type.inherit(prop_name, iter_values())
    else:
      if self.exported_props.is_set(prop_name):
        return self.exported_props[prop_name]
      elif self.props.is_set(prop_name):
        return self.props[prop_name]
      elif default is NotImplemented:
        return self.context.target_properties[prop_name].get_default()
      else:
        return default

  def get_props(self, prefix='', as_object=False):
    """
    Returns a dictionary that contains all property values, optionally from
    the specified prefix.
    """

    result = {}
    propset = self.context.target_properties
    for prop in filter(lambda x: x.name.startswith(prefix), propset.values()):
      inherit = prop.options.get('inherit', False)
      value = self.get_prop(prop.name, inherit)
      result[prop.name[len(prefix):]] = value

    if as_object:
      result = ObjectFromMapping(result)

    return result

  def transitive_dependencies(self):
    def worker(target, private=False):
      for dep in target.dependencies:
        if dep.public or private:
          yield dep
        for t in dep.sources:
          yield from worker(t)
    return stream.unique(worker(self, private=True))

  def add_dependency_with_class(self, dependency_cls, sources, public=False):
    dep = dependency_cls(self, sources, public)
    self.dependencies.append(dep)
    return dep

  def add_dependency(self, *args, **kwargs):
    return self.add_dependency_with_class(Dependency, *args, **kwargs)

  def add_action(self, name=None, *, input=None, output=None, deps=None, **kwargs):
    """
    Creates a new action in the target that consists of one or more system
    commands. Unless otherwise explicitly set with the *input* or *deps*
    parameters, the first action that is being created for a target will have
    the *input* parameter default to #True, in which case it will be connected
    to all outputs of the dependencies of this target.

    Dependencies can also be specified explicitly by passing a list of #Action
    objects to the *deps* parameter.

    Otherwise, actions created after the first will receive the previously
    created action as dependency.

    Passing #True for *output* will mark the action as an output action,
    which will be connected with the actions generated by the dependents of
    this target (unless they explicitly specifiy the dependencies).
    To explicitly mark an action as NO output action, set *output* to #False.

    All other arguments are forwarded to the #Action constructor.
    """

    if self.redirect_actions:
      return self.parent(name, input=input, output=output, deps=deps, **kwargs)

    if name is None:
      # TODO: Automatically add the name of the program in the first command.
      name = str(len(self.actions))

    if name in self.actions:
      raise ValueError('action name already used: {!r}'.format(name))

    if input is None:
      input = not self.actions
    if deps is None:
      deps_was_unset = True
      deps = []
    else:
      deps_was_unset = False
      deps = list(deps)
    if input:
      for dep in self.transitive_dependencies():
        for target in dep.sources:
          deps += target.output_actions
    elif deps_was_unset and self.actions:
      output_actions = self.output_actions
      if output_actions:
        deps.append(output_actions[-1])

    # Filter 'None' values from the actions list.
    deps = [x for x in deps if x is not None]

    # TODO: Assign the action to the pool specified in the target.
    kwargs.setdefault('explicit', self.get_prop('this.explicit'))
    kwargs.setdefault('syncio', self.get_prop('this.syncio'))
    action = Action(self.id, name, deps=deps, **kwargs)
    self.actions[name] = action
    action.is_output = output
    return action

  def actions_and_files_tagged(self, tags, transitive=False):
    """
    Returns a tuple of (actions, files) where *actions* is a list of actions
    in the target that have at least one buildset where the specified *tags*
    match, and *files* is a list of the files that match these tags.

    If *transitive* is #True, the actions and files of the transitive
    dependencies are returned instead.
    """

    if self.redirect_actions:
      return self.parent.actions_and_files_tagged(tags, transitive)

    if isinstance(tags, str):
      tags = [x.strip() for x in tags.split(',')]

    actions = []
    files = []
    if transitive:
      for target in self.transitive_dependencies().attr('sources').concat():
        res = target.actions_and_files_tagged(tags)
        actions += res[0]
        files += res[1]
    else:
      for action in self.actions.values():
        matched_files = action.all_files_tagged(tags)
        if matched_files:
          actions.append(action)
          files += matched_files

    return actions, files

  def files_tagged(self, tags, transitive=False):
    """
    Returns only files with the specified tags.
    """

    if self.redirect_actions:
      return self.parent.files_tagged(tags, transitive)
    return self.actions_and_files_tagged(tags, transitive)[1]

  def iter_layers(self):
    return iter(self._layers_list)

  def add_layer_with_class(self, target_cls, name, public=False, redirect_actions=False):
    if name in self.layers:
      raise ValueError('Target layer {!r} already exists'.format(name))
    target = target_cls(self.module, name, public, parent=self,
      redirect_actions=redirect_actions)
    self.layers[name] = target
    self._layers_list.append(target)
    return target

  def add_layer(self, *args, **kwargs):
    return self.add_layer_with_class(type(self), *args, **kwargs)


class Dependency:
  """
  Resembles a dependency to one or more other targets.
  """

  @staticmethod
  def setup_standard_properties(propset):
    pass

  def __init__(self, target, sources, public):
    if isinstance(sources, collections.Iterator):
      sources = list(sources)
    sources = proplib.List[proplib.InstanceOf[Target]]().coerce('sources', sources)
    self.target = target
    self.sources = sources
    self.public = public
    self.props = proplib.Properties(target.context.dependency_properties, self)

  def __repr__(self):
    return 'Dependency({!r}, {!r}, public={!r})'.format(
      self.target, self.sources, self.public)

  @property
  def context(self):
    return self.target.context


class TargetHandler:
  """
  Interface for target handlers -- the objects that are capable of taking
  target properties and their dependencies and converting them to build
  actions.
  """

  def init(self, context):
    pass

  def target_created(self, target):
    pass

  def translate_begin(self):
    pass

  def preprocess_target(self, target):
    pass

  def translate_target(self, target):
    pass

  def translate_end(self):
    pass

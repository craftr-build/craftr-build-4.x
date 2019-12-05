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

from nr.stream import Stream

import abc
import collections
import {ObjectFromDict} from './utils/maps'
import {Action, ActionSet, BuildGraph, FileSet} from './build'
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
    """
    Register a #TargetHandler to the Context. The handler will be inserted
    at the first position into the #handlers list and
    #TargetHandler.on_register() will be called.

    Note: The reverse order of registration is the order in which target
    handlers will be invoked during the translation process.
    """

    handler.on_register(self)
    self.handlers.insert(0, handler)

  def iter_targets(self):
    """
    Iterates over all targets in the context in post-order, including layers.
    """

    seen = set()

    def recurse_target(target):
      for dep in target.transitive_targets():
        if dep in seen: continue
        seen.add(dep)
        yield dep
        yield from recurse_layers(dep)
        yield from recurse_target(dep)

    def recurse_layers(target):
      for layer in target.iter_layers():
        if layer in seen: continue
        seen.add(layer)
        yield layer
        yield from recurse_target(layer)

    for module in self.modules:
      for target in module.targets.values():
        yield from recurse_target(target)
        yield target
        yield from recurse_layers(target)

  def iter_targets_additive(self):
    """
    Iterates over all targets in the context in post-order, including layers,
    until no more targets are unseen. This is used during #translate_targets()
    to account for new layers being created in targets during iteration.
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
    Performs the translation process for all targets in all modules. It uses
    #iter_targets_additive() to account for new layers that are created during
    the translation process.
    """

    for target in self.iter_targets_additive():
      for handler in self.handlers:
        handler.on_target_translate(self, target)

    for target in self.iter_targets():
      self.graph.add_actions(target.actions.values())


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
    return '{}(name={!r}, version={!r}, directory={!r})'.format(
      type(self).__name__, self.name, self.version, self.directory)

  def add_target_with_class(self, target_cls, name, public=False):
    if name in self.targets:
      raise ValueError('target name {!r} already occupied'.format(name))
    target = target_cls(self, name, public)
    self.targets[target.name] = target
    for handler in self.context.handlers:
      handler.on_target_created(self.context, target)
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
    self.input_actions = []
    self.layers = collections.OrderedDict()
    self._layers_list = []  # Can be appended to during iteration.

  def __repr__(self):
    return '{}(id={!r}, public={!r})'.format(
      type(self).__name__, self.id, self.public)

  def __getitem__(self, prop_name):
    prop = self.context.target_properties[prop_name]
    inherit = prop.options.get('inherit', False)
    return self.get_prop(prop_name, inherit=inherit)

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
    """
    Returns the value of the `this.directory` property of the target. If the
    property is not explicitly set, falls back on the directory of the parent
    target or that of the owning #Module.

    The `this.directory` property will be used to convert any relative paths
    to absolute paths in properties of type #proplib.Path or #proplib.PathList.
    """

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
    Returns a property value. If a value exists in #exported_props and #props,
    the #exported_props takes preference.

    If *inherit* is #True, the property must be a #proplib.List property
    and the values in the exported and non-exported property containers as
    well as transitive dependencies are respected.

    Note that this method does not take property options into account, so
    even if you specified `options={'inherit': True}` on the property you
    want to retrieve, you will need to pass `inherit=True` explicitly to this
    method. If you want this to happen automatically, use the #__getitem__().
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
    Creates a dictionary from all property values in the Target that start
    with the specified *prefix*. If *as_object* is #True, an object that wraps
    the dictionary will be returned instead. Modifying the returned dictionary
    does not have an effect on the actualy property values of the Target.

    The prefix will be stripped from the keys (or attributes) of the returned
    dictionary (or object).

    # Parameters
    prefix (str): The prefix to filter properties.
    as_object (bool): Return an object instead of a dictionary.
    return (dict, ObjectFromDict)
    """

    result = {}
    propset = self.context.target_properties
    for prop in filter(lambda x: x.name.startswith(prefix), propset.values()):
      result[prop.name[len(prefix):]] = self[prop.name]

    if as_object:
      result = ObjectFromDict(result)

    return result

  def transitive_dependencies(self):
    """
    Returns an iterator that yields the #Dependencies<Dependency> of the
    Target including transitively inherited dependencies. The returned
    iterator is a #stream instance, thus you can use any streaming operations
    on the returned object.

    For example, to iterate over all targets contained in the dependencies,
    you can use

    ```python
    for other_target in target.transitive_dependencies()\
                          .attr('sources').concat().unique():
      # ...
    ```

    But there's a shortcut for that one: #transitive_targets().
    """

    def worker(target, private=False):
      for dep in target.dependencies:
        if dep.public or private:
          yield dep
        for t in dep.sources:
          yield from worker(t)
    return Stream.unique(worker(self, private=True))

  def transitive_targets(self):
    """
    Returns an iterator that yields a namedtuple of #Dependency and #Target
    objects listed in the dependencies of this target. The returned iterator
    is a #stream instance, thus you can use any streaming operations on the
    object.
    """

    return self.transitive_dependencies().attr('sources').concat().unique()

  def transitive_target_pairs(self):
    """
    Similar to #transitive_targets(), but yields pairs of #Dependency and
    #Target objects instead.
    """

    DependencyTargetPair = collections.namedtuple(
      'DependencyTargetPair', ('dep', 'target'))

    def generate():
      seen = ()
      for dependency in self.transitive_dependencies():
        for target in dependency.sources:
          if target not in seen:
            yield DependencyTargetPair(dependency, target)
            seen.add(target)

    return stream(generate())

  def add_dependency_with_class(self, dependency_cls, sources, public=False):
    dep = dependency_cls(self, sources, public)
    self.dependencies.append(dep)
    return dep

  def add_dependency(self, *args, **kwargs):
    """
    Add a new dependency to this target that references the targets specified
    in the *sources* parameter.

    # Parameters
    sources (Target, list of Target):
      A target or a list of targets that the dependency references.
    public (bool):
      Pass #True if you want the dependency to be public, which means that
      targets that depend on _this_ target will inherit the dependency in
      #transitive_dependencies().
    return (Dependency)
    """

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
      for target in self.transitive_targets():
        deps += target.output_actions
      deps = list(Stream.chain(deps, self.input_actions).unique())
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

  def add_input_action(self, action):
    """
    Adds an #Action to this target as an explicit input action. This action
    is taken into account when using #add_action() the same as for the output
    actions of the target's dependencies.
    """

    assert isinstance(action, Action)
    self.input_actions.append(action)

  def iter_layers(self, recursive=False):
    """
    Returns an iterator for the layers in this target. If *recursive* is
    #True, the iterator will include layers of layers.
    """

    for layer in self._layers_list:
      yield layer
      if recursive:
        yield from layer.layers(True)

  def add_layer_with_class(self, target_cls, name, public=False, redirect_actions=False):
    if name in self.layers:
      raise ValueError('Target layer {!r} already exists'.format(name))
    target = target_cls(self.module, name, public, parent=self,
      redirect_actions=redirect_actions)
    self.layers[name] = target
    self._layers_list.append(target)
    return target

  def add_layer(self, *args, **kwargs):
    """
    Add a new layer to the Target. A layer is also just a Target, but listed
    as a child of the current target. This layer can be used to specify new
    properties that can be taken into account by #TargetHandler implementations
    independent of the parent target.

    If you want the parent target to be taken into account when the layer
    is translated, add it as a dependency with #add_dependency().

    # Parameters
    name (str):
      The name of the layer. This name must be unique inside the layers of
      this target.
    public (bool):
      Whether the new layer is a public target that will be referenced by
      default when declaring a dependency to the owning module.
    redirect_actions (bool):
      If this is #True, actions created in the layer will be added to the
      parent target instead. This is usually not recommended.
    return (Target)
    """

    return self.add_layer_with_class(type(self), *args, **kwargs)

  def actions_for(self, tags, transitive=False):
    """
    Returns a set of #Action#s that that have a buildset with files that
    match the specified *tags*. If *transitive* is #True, the actions of
    the target's dependencies will be taken into account as well.

    #TargetHandler implementations should use this method to take into
    account any generated files that they might be able to handle further.
    For example, a #TargetHandler that preprocesses C++ source code should
    tag the output files as `out,cxx.cpp` so that the Cxx #TargetHandler can
    retrieve these files with `out,cxx.cpp,!used` and include them in the
    compilation.

    Note that the files taken into account should then be tagged as `used`
    in order to avoid other targets inheriting these files as well. This
    can be done conveniently with the #ActionSet.tag() method.

    In order to get a list of the files that matches the tags, use the
    #ActionSet.files iterator. Make sure that when you use this method in
    a #TargetHandler to retrieve additional input files that you add the
    returned actions to the actions that your handler creates (with
    #ActionSet.__iter__()).

    # Parameters
    tags (str, list of str):
      A file tag string or list of file tags.
    transitive (bool):
      If #True, take actions of the target's dependencies into account as well.
    return (ActionSet)
    """

    if self.redirect_actions:
      return self.parent.actions_and_files_tagged(tags, transitive)

    if isinstance(tags, str):
      tags = [x.strip() for x in tags.split(',')]

    result = ActionSet(tags)
    if transitive:
      for target in self.transitive_targets():
        result |= target.actions_for(tags, transitive=False)
    else:
      for action in self.actions.values():
        if action.has_files_tagged(tags):
          result.add(action)

    return result


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
    return '{}({!r}, {!r}, public={!r})'.format(
      type(self).__name__, self.target, self.sources, self.public)

  @property
  def context(self):
    return self.target.context


class TargetHandler(metaclass=abc.ABCMeta):
  """
  TargetHandlers are responsible for taking into account the properties on
  a target and translating that information to actions in the build graph.

  Every TargetHandler gets the chance to register new properties in the
  #on_register() method. These properties should have a common prefix.

  Some TargetHandlers may want to run before others. This is entirely
  based on the order that handlers are registered with
  #Context.register_handler(). If you want your target handler to run
  before another, make sure to import the module that implements the
  target handler before you register your handler.
  """

  @abc.abstractmethod
  def on_register(self, context):
    """
    This method is called when the TargetHandler is registered to the
    context with #Context.register_handler(). This is the chance for the
    the TargetHandler to register any properties that it can support on
    modules, targets and dependencies.
    """

    pass

  def on_target_created(self, context, target):
    """
    This method is called when a target is created with #Module.add_target().
    Note that it can only be called for targets that are created after the
    TargetHandler was registered.
    """

    pass

  @abc.abstractmethod
  def on_target_translate(self, context, target):
    """
    This method is called when the target is supposed to be translated into
    build actions. Use the #Target.add_action() method to create a build
    action.

    The TargetHandler may also add another layer to the target using the
    #Target.add_layer() method. This returns a new #Target instance which
    is a child of the original target, and it will go through the same
    translation process after this method completes. Note that it is not
    garuanteed that the layer will be handled right after this method.
    Generally speaking, the current target will be run through all handlers
    before continuing with the newly created layer. TargetHandlers usually
    add the parent target as to the new layers as a dependency with
    #Target.add_dependency().

    Also keep in mind that a layer introduces a new target name (the
    parent target name and the layer name separated by a slash).

    TargetHandlers usually not only take the properties of the current target
    into account, but also the properties and output files of the targets that
    are listed as dependencies. Use the #Target.transitive_dependencies()
    method to iterate over all #Dependency objects of the target that should
    be taken into account.
    """

    pass

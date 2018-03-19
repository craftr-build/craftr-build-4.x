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

from . import proplib
from nr.stream import stream


class Context:
  """
  The context contains global information for the build system.
  """

  def __init__(self):
    self.target_properties = proplib.PropertySet()
    Target.setup_standard_properties(self.target_properties)
    self.dependency_properties = proplib.PropertySet()
    Dependency.setup_standard_properties(self.dependency_properties)
    self.handlers = []
    self.modules = {}

  def register_handler(self, handler):
    handler.init(self)
    self.handlers.append(handler)

  def translate_targets(self):
    """
    Invokes the translation process for all targets in all modules in the
    Context.
    """

    for handler in self.handlers:
      handler.translate_begin()

    seen = set()
    def translate(target):
      for dep in target.dependencies:
        for other_target in dep.sources:
          translate(other_target)
      if target not in seen:
        seen.add(target)
        for handler in self.handlers:
          handler.translate_target(target)

    for module in self.modules.values():
      for target in module.targets.values():
        translate(target)

    for handler in self.handlers:
      handler.translate_end()

    for module in self.modules.values():
      for target in module.targets.values():
        self.build_graph.add_actions(target.actions.values())


class Module:
  """
  Represents a namespace for targets. Every build script in the Craftr DSL
  has its own namespace, which must be explicitly declared with the `namespace`
  keyword. Additionally, a version number may be declared which can be used
  by target handlers for default filenames, etc. Every namespace is also
  associated with a directory that all paths, if they are not absolute, should
  be treated relative to.
  """

  def __init__(self, context, name, version, directory):
    self.context = context
    self.name = name
    self.version = version
    self.directory = directory
    self.targets = {}

  def __repr__(self):
    return 'Module(name={!r}, version={!r}, directory={!r})'.format(
      self.name, self.version, self.directory)

  def add_target(self, name, public):
    if name in self.targets:
      raise ValueError('target name {!r} already occupied'.format(name))
    target = Target(self, name, public)
    self.targets[target.name] = target
    return target


class Target:
  """
  A target represents a collection of properties and dependencies to other
  targets. Targets will be translated into build actions by target handlers
  based on their properties and dependencies.
  """

  @staticmethod
  def setup_standard_properties(propset):
    propset.add('this.directory', proplib.String)
    propset.add('this.pool', proplib.String)
    propset.add('this.explicit', proplib.Bool, default=False)
    propset.add('this.syncio', proplib.Bool, default=False)

  def __init__(self, module, name, public):
    self.module = module
    self.name = name
    self.public = public
    self.props = proplib.Properties(module.context.target_properties)
    self.exported_props = proplib.Properties(module.context.target_properties)
    self.dependencies = []

  def __repr__(self):
    return 'Target(id={!r})'.format(self.id)

  def get_prop(self, prop_name):
    """
    Returns a property value, preferring the value in the #exported_props.
    """

    if self.exported_props.is_set(prop_name):
      return self.exported_props[prop_name]
    else:
      return self.props[prop_name]

  def get_prop_join(self, prop_name):
    """
    Returns a property value, taking the #exported_props and #props into
    account as well as the values from all the target's dependencies.
    """

    def iter_dep_targets(target):
      for dep in target.dependencies:
        yield from dep.sources
        for t in dep.sources:
          yield from iter_dep_targets(t)

    def iter_values():
      yield self.exported_props[prop_name]
      yield self.props[prop_name]
      for target in stream.unique(iter_dep_targets(self)):
        yield target.exported_props[prop_name]

    prop = self.context.target_properties[prop_name]
    return prop.type.inherit(iter_values())

  @property
  def context(self):
    return self.module.context

  @property
  def id(self):
    return '{}@{}'.format(self.module.name, self.name)

  @property
  def directory(self):
    return self.exported_props['this.directory'] or self.props['this.directory'] or self.module.directory

  def add_dependency(self, sources, public):
    dep = Dependency(self, sources, public)
    self.dependencies.append(dep)
    return dep


class Dependency:
  """
  Resembles a dependency to one or more other targets.
  """

  @staticmethod
  def setup_standard_properties(propset):
    pass

  def __init__(self, target, sources, public):
    self.target = target
    self.sources = sources
    self.public = public
    self.props = proplib.Properties(target.context.dependency_properties)

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

  def translate_begin(self):
    pass

  def translate_target(self, target):
    pass

  def translate_end(self):
    pass


import collections
import os
import re
import sys

from . import path, props


def with_plural(x, noun):
  if x != 1:
    noun += 's'
  return '{} {}'.format(x, noun)


def validate_module_name(name):
  if not re.match('^[\w\d_\-/]+$', name):
    raise ValueError('invalid module name: {!r}'.format(name))


def validate_target_name(name):
  if not re.match('^[\w\d_\-]+$', name):
    raise ValueError('invalid target name: {!r}'.format(name))


def validate_action_name(name):
  if not re.match('^[\w\d_\-\.]+$', name):
    raise ValueError('invalid action name: {!r}'.format(name))


Pool = collections.namedtuple('Pool', 'name depth')


class TaggedFile:
  """
  Represents a file attached with zero or more tags.

  This class interns all tag strings.
  """

  def __init__(self, name, tags=()):
    self._name = name
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


class FileSet:
  """
  Represents a collection of #TaggedFile objects. Additionally, the #FileSet
  may contain additional variables with lists of strings a values. These may
  not be useful in all contexts.
  """

  def __init__(self):
    self._files = collections.OrderedDict()

  def __repr__(self):
    v = ('{!r}: {!r}'.format(k, v.tags) for k, v in self._files.items())
    return 'FileSet({{{0}}})'.format(', '.join(v))

  def __getitem__(self, name):
    name = path.canonical(name)
    return self._files[name.lower()]

  def __delitem__(self, name):
    name = path.canonical(name)
    del self._files[name]

  def name(self):
    return self._name

  def add(self, names, tags=()):
    if isinstance(names, str):
      names = [names]
    result = []
    for name in names:
      name = path.canonical(name)
      # We build the hash table using the case-insensitive canonical name.
      name_lower = name.lower()
      obj = self._files.get(name_lower)
      if obj is None:
        obj = TaggedFile(name, tags)
        self._files[name_lower] = obj
      else:
        obj.add_tags(tags)
      result.append(obj)
    return result

  def files(self, tags=None):
    for tf in self._files.values():
      if tags is None or all(x in tf.tags for x in tags):
        yield tf


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
    self._outputs = FileSet()
    self._handler_data = {}
    self._actions = collections.OrderedDict()
    self._output_actions = []
    self._eval_namespace = props.duplicate_namespace(
      module.eval_namespace(), 'target "{}"'.format(name))
    self._eval_namespace.target = self
    self.define_property('this.pool', 'String', None, inheritable=False)
    self.define_property('this.syncio', 'Bool', False, inheritable=False)
    self.define_property('this.explicit', 'Bool', False, inheritable=False)
    self.define_property('this.directory', 'String', None, inheritable=False)

  def __repr__(self):
    return 'Target({!r} of {})'.format(self._name, self._module)

  def module(self):
    return self._module

  def name(self):
    return self._name

  def identifier(self):
    return '{}/{}'.format(self._module.name(), self._name)

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
    return self._outputs

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

  def actions(self):
    return self._actions.values()

  def output_actions(self):
    return iter(self._output_actions)

  def add_action(self, name=None, *, input=None, output=False, deps=None, **kwargs):
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

    All other arguments are forwarded to the #Action constructor.
    """

    if name is None:
      # TODO: Automatically add the name of the program in the first command.
      name = str(len(self._actions))
    validate_action_name(name)
    if name in self._actions:
      raise ValueError('action name already used: {!r}'.format(name))

    if input is None:
      input = not self._actions
    if deps is None:
      deps_was_unset = True
      deps = []
    else:
      deps_was_unset = False
      deps = list(deps)
    if input:
      for dep in self.transitive_dependencies():
        for target in dep.targets():
          deps += target.output_actions()
    elif deps_was_unset and self._actions:
      if self._output_actions:
        deps.append(self._output_actions[-1])
      else:
        # The last added action.
        assert isinstance(self._actions, collections.OrderedDict)
        deps.append(self._actions[next(reversed(self._actions))])

    # TODO: Assign the action to the pool specified in the target.
    kwargs.setdefault('explicit', self.get_property('this.explicit'))
    kwargs.setdefault('syncio', self.get_property('this.syncio'))
    action = Action(self, name, deps=deps, **kwargs)
    self._actions[name] = action
    if output:
      self._output_actions.append(action)
    return action

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
    self.define_property('this.select', 'StringList', [], inheritable=False)

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
      select = self.get_property('this.select')
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


class Action:
  """
  Represents an action that translates a set of input files to a set of
  output files. Actions can be used to execute the *commands* multiple
  times for different sets of input/output files. Every action needs at
  least one set of input/output files.

  # Variables
  Every file in an action has a tag associated with it. Files can then be
  accessed by filtering with these tags. To reference files that have a tag,
  use the `$tag` or `${tag}` syntax inside the command list. Multiple tags
  can be separated by `&` characters. Files need all tags specified in a
  variable to match, eg. `${out&dll}` will be expanded to all files that are
  tagged as `out` and `dll`.

  Note that an argument in the command-list will be multiplied for every
  file matching the variable, eg. an argument "-I${include}" may expand to
  multiple arguments like `-Iinclude`, `-Ivendor/optional/include` if there
  are multiple files with the tag `include`.

  Note that only files tagged with `in` and `out` will be considered mandatory
  input and output files for an action. Additionally, the tag `optional` may
  be combined with any of the two tags to specify an optional input or output
  file.

  # Parameters
  target (Target):
    The #Target that this action is generated for. Note that in a session
    where the build graph is loaded from a file and the build modules have
    not been executed, this may be a proxy target with no valid properties.
  name (str):
    The name of the action inside the target.
  commands (list of list of str):
    A list of commands to execute in order. The strings in this list may
    contain variables are described above.
  deps (list of Action):
    A list of actions that need to be executed before this action. This
    relationship should also roughly be represented by the input and output
    files of the actions.
  cwd (str):
    The directory to execute the action in.
  environ (dict of (str, str)):
    An environment dictionary that will be merged on top of the current
    environment before running the commands in the action.
  explicit (bool):
    If #True, this action must be explicitly specified to be built or
    required by another action to be run.
  syncio (bool):
    #True if the action needs to be run with the original stdin/stdout/stderr
    attached.
  deps_prefix (str): A string that represents the prefix of for lines
    in the output of the command(s) that represent additional dependencies
    to the action (eg. headers in the case of C/C++). Can not be mixed with
    *depfile*.
  depfile (str): A filename that is produced by the command(s) which lists
    additional dependencies of the action. The file must be formatted like
    a Makefile. Can not be mixed with *deps_prefix*.

  # Members
  builds (list of BuildSet):
    A list of files this action depends on or produces and variables. Both
    are available for variable expansion in the *commands* strings.
  """

  class ActionVariables:
    """
    A container for variables that must be lists of strings. Used in an
    action's build step together with a #FileSet.
    """

    def __init__(self):
      self._variables = collections.OrderedDict()

    def __repr__(self):
      v = ('{!r}: {!r}'.format(k, v) for k, v in self._variables.items())
      return 'ActionVariables({{{}}})'.format(', '.join(v))

    def __getitem__(self, key):
      return self._variables[key]

    def __setitem__(self, key, value):
      if not isinstance(value, (list, tuple)):
        raise TypeError('expected List/Tuple, got {}'.format(type(value).__name__))
      if not all(isinstance(x, str) for x in value):
        raise TypeError('expected item to be str')
      self._variables[key] = list(value)

    def __delitem__(self, key):
      del self._variables[key]

    def __contains__(self, key):
      return key in self._variables

    def get(self, key, default=None):
      return self._variables.get(key, default)

  BuildSet = collections.namedtuple('BuildSet', 'name files vars')

  def __init__(self, target, name, deps, commands, cwd=None, environ=None,
               explicit=False, syncio=False, deps_prefix=None, depfile=None):
    validate_action_name(name)
    assert isinstance(target, Target)
    assert all(isinstance(x, Action) for x in deps)
    self.target = target
    self.name = name
    self.deps =deps
    self.commands = commands
    self.cwd = cwd
    self.environ = environ
    self.explicit = explicit
    self.syncio = syncio
    self.deps_prefix = deps_prefix
    self.depfile = depfile
    self.builds = []

  def __repr__(self):
    return 'Action({!r} with {})'.format(
      self.identifier(), with_plural(len(self.builds), 'buildset'))

  def identifier(self):
    return '{}:{}'.format(self.target.identifier(), self.name)

  def add_buildset(self, name=None):
    buildset = self.BuildSet(name, FileSet(), self.ActionVariables())
    self.builds.append(buildset)
    return buildset


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

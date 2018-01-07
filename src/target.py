
import collections
import re
import craftr from './index'
import utils from './utils'
import path from './utils/path'
import {BuildAction} from './buildgraph'


def splitref(s):
  """
  Splits a target reference string into its namespace and target component.
  A target reference must be of the format `//<namespace>:<target>` or
  `:<target>`. For the latter form, the returned namespace will be #None.
  """

  if not isinstance(s, str):
    raise TypeError('target-reference must be a string', s)
  if ':' not in s:
    raise ValueError('invalid target-reference string: {!r}'.format(s))
  namespace, name = s.partition(':')[::2]
  if namespace and not namespace.startswith('//'):
    raise ValueError('invalid target-reference string: {!r}'.format(s))
  if namespace:
    namespace = namespace[2:]
    if not namespace:
      raise ValueError('invalid target-reference string: {!r}'.format(s))
  return namespace or None, name


def joinref(namespace, name):
  if namespace:
    return '//{}:{}'.format(namespace, name)
  else:
    return ':{}'.format(name)


def resolve(target):
  """
  Resolve a target identifier string of the format `[//<namespace>]:target`.
  If *target* is already a #Target instance, it is returned as-is.
  """

  if isinstance(target, Target):
    return target
  namespace, target = splitref(target)
  namespace = Namespace.current() if not namespace else Namespace.get(namespace)
  try:
    return namespace.targets[target]
  except KeyError:
    msg = 'cell or target does not exist: {!r}'
    raise ValueError(msg.format(joinref(namespace.name, target)))


class Namespace:
  """
  The namespace represents a scope for targets and usually reflects a project
  root directory on the filesystem.
  """

  NAMESPACES = {}

  def __init__(self, name, version, directory, build_directory=None):
    assert isinstance(name, str)
    assert re.match('[A-z0-9@_\\-/]+', name), repr(name)

    self.name = name
    self.version = version
    self.directory = directory
    if not build_directory:
      build_directory = path.join(craftr.build_directory, 'cells', self.name)
    self.build_directory = build_directory
    self.targets = {}

  def __repr__(self):
    return '<Namespace {!r} directory={!r} len(targets)={}>'.format(
        self.name, self.directory, len(self.targets))

  def add_target(self, target):
    """
    Adds a #Target to the namespace. This method is automatically called from
    the #Target constructor, thus it does not need to be called explicitly.
    """

    if target.namespace is not self:
      raise RuntimeError('Target "{}" is already in namespace "{}", can not '
        'add to cell "{}"'.format(target.name, target.namespace.name, self.name))
    if target.name in self.targets:
      raise RuntimeError('Target "{}" already exists in namespace "{}"'
        .format(target.name, self.name))
    self.targets[target.name] = target

  @classmethod
  def from_module(cls, module):
    package = module.package
    if hasattr(module.namespace, 'namespace'):
      name = module.namespace.namespace
      version = getattr(module.namespace, 'project_version', '1.0.0')
      directory = getattr(module.namespace, 'project_directory', None)
      if not directory:
        directory = str(module.directory)
    else:
      name = '__main__' if not package else package.name
      version = '1.0.0' if not package else package.payload.get('version', '1.0.0')
      directory = require.main.directory if not package else str(package.directory)
    namespace = cls(name, version, directory)
    return namespace

  @classmethod
  def current(cls, create=True):
    package = require.current.package
    if not package and require.current != require.main and not hasattr(require.current.namespace, 'namespace'):
      raise RuntimeError('can not create Namespace for non-main script '
                        'without an associated Node.py package')
    namespace = cls.from_module(require.current)
    if create:
      return cls.NAMESPACES.setdefault(namespace.name, namespace)
    else:
      return cls.NAMESPACES[namespace.name]

  @classmethod
  def get(cls, name):
    return cls.NAMESPACES[name]

  @classmethod
  def all(cls):
    return cls.NAMESPACES.values()


class Target:
  """
  A Target is a task in the build graph that may depend on other targets.
  Usually, a target converts a set of input files to one or more output files.

  Targets are structured hierarchically while at the same time being connected
  in a graph as represented by a targets private and public dependencies. A
  target may consist of multiple child targets and depend on any number of
  other targets.

  Every target has a unique identifier that is constructed from the target's
  namespace, its parent target and its own name. The target identifier has the
  format `//<namespace>:[<parent>/[...]]<name>`.

  A target can have two kinds of dependencies: private and public. Private
  dependencies can be taken into account by the target itself, but they can
  not be taken into account transitively by targets that depend on another
  target. Public dependencies can be taken into account transitively.

  The behaviour of targets is implemented via the #Behaviour interface.
  """

  def __init__(self, namespace, name, impl_class=None, explicit=False, console=False):
    assert isinstance(namespace, Namespace), type(namespace)
    assert isinstance(name, str) and len(name) > 0, repr(name)
    assert re.match('[A-z0-9@_\\-]+', name), repr(name)

    self.__parent = None
    self.__namespace = namespace
    self.__children = ChildrenList(self)
    self.__name = name
    self.__private_deps = DependencyList(self)
    self.__public_deps = DependencyList(self)
    self.__dependents = []
    self.__impl = impl_class(self) if impl_class is not None else None
    self.__actions = collections.OrderedDict()
    self.__output_actions = []
    self.__is_translated = False
    self.explicit = explicit
    self.console = console
    namespace.add_target(self)

  parent = utils.getter('_Target__parent')
  namespace = utils.getter('_Target__namespace')
  children = utils.getter('_Target__children')
  name = utils.getter('_Target__name')
  private_deps = utils.getter('_Target__private_deps')
  public_deps = utils.getter('_Target__public_deps')
  impl = utils.getter('_Target__impl')

  @parent.setter
  def parent(self, target):
    if self.__parent:
      self.__parent.children.remove(self)
    target.children._ChildrenList__items.append(self)
    self.__parent = target

  @impl.setter
  def impl(self, impl):
    if not isinstance(impl, Behaviour):
      raise TypeError('expected Behaviour, got {}'.format(type(impl).__name__))
    if impl.target is not self:
      raise RuntimeError('can not set behaviour if it doesn\'t point to this target')
    self.__impl = impl

  def __repr__(self):
    return '<Target {!r}>'.format(self.identifier())

  def long_name(self):
    result = self.name
    parent = self.parent
    while parent:
      result = parent.name + '/' + result
      parent = parent.parent
    return result

  def identifier(self):
    return '//{}:{}'.format(self.namespace.name, self.long_name())

  def deps(self, transitive=True, children=True, parent=True, with_behaviour=None):
    """
    Returns an #utils.stream object that yields the dependencies of this
    target. This includes the private dependencies of *self*. If the
    *transitive* parameter is set to #False, only the #public_deps and
    #private_deps of *self* are returned.
    """

    def recursion(targets):
      yield from targets
      if transitive or children:
        for other in targets:
          if transitive:
            yield from recursion(other.public_deps)
          if children and other != self.__parent:
            # A target may add itself to the dependencies of one of its
            # child targets, in that case however we do not want to
            # include it's children again.
            yield from recursion(other.children)

    stream = utils.stream.chain(
      recursion(self.private_deps),
      recursion(self.public_deps)
    )
    if parent and self.__parent:
      stream = stream.chain(self.__parent.deps(transitive, children, False))
    if with_behaviour is not None:
      stream = stream.filter(lambda x: isinstance(x.impl, with_behaviour))
    return stream.unique()

  def dependents(self, transitive=False, with_behaviour=None):
    """
    Returns an #utils.stream that contains all targets that depend on this
    target. If *transitive* is #False, only the direct dependents of the
    target are returned.
    """

    def recursion(targets):
      yield from targets
      if transitive:
        for other in targets:
          yield from recursion(other.__dependents)

    stream = utils.stream(recursion(self.__dependents))
    if transitive and self.__parent:
      stream = stream.chain(self.__parent.dependents(True))
    if with_behaviour is not None:
      stream = stream.filter(lambda x: isinstance(x.impl, with_behaviour))
    return stream.unique()

  def add_dependency(self, target, transitive=False):
    """
    Adds the target *target* to the list of dependencies in *self*. If the
    *transitive* argument is set to #True, the target is instead added to the
    list of public dependencies.

    The *target*'s dependents list is updated respectively.
    """

    dest = self.__public_deps if transielse else self.__private_deps
    if target not in dest:
      dest.append(target)
    if self not in target.__dependents:
      target.__dependents.append(self)

  def add_action(self, name, commands, input_files=None, output_files=None,
        optional_output_files=None, files=None, input=None, deps=None,
        output=False, cwd=None, environ=None, foreach=False):
    """
    Creates a new action in the target that consists of one or more system
    commands and the specified *name*. Unless otherwise explicitly stated
    with the *input* or *deps* parameters, the first action that is being
    created for a #Target will be have the *input* parameter default to #True,
    in which case it will be connected to all outputs of the dependencies of
    this target.

    Alternatively, dependencies can be managed explicitly by passing the
    *deps* parameter, which must be an iterable of #BuildAction#s or #Target#s.
    In the case of a #Target, all output actions of that target are considered.

    If no explicit *deps* are specified, actions created after the first will
    receive the previously created action as dependency.

    Passing #True for the *output* parameter will mark the action as an output
    action, which will be connected with the actions generated by the
    #Target.dependents.

    The *input_files* and *output_files* may be a list of filenames, or a
    nested list where each item is a list of input files and output files
    respectively. The nested version should only be used for a for-each
    action.
    """

    assert name is None or re.match('[A-z0-9_\-]', name), repr(name)
    assert isinstance(commands, (list, tuple)), type(commands)
    assert all(isinstance(x, (list, tuple)) for x in commands)
    assert all(isinstance(x, str) for l in commands for x in l)

    if name is None:
      name = str(len(self.__actions))
    if name in self.__actions:
      raise ValueError('Action name already used: {!r}'.format(name))

    if input and deps is not None:
      raise ValueError('invalid combination of arguments (input~=True && deps!=None)')
    if input or (input is None and not self.__actions):
      deps = list(self.deps(transitive=True))
    elif deps is None and self.__actions:
      deps = [self.__last_action()]

    actual_deps = []
    for dep in deps:
      if isinstance(dep, Target):
        actual_deps.extend(dep.actions(outputs=True))
      elif isinstance(dep, BuildAction):
        actual_deps.append(dep)
      else:
        msg = 'Action deps must be Target or BuildAction, got {!r}'
        raise ValueError(msg.format(type(dep).__name__))

    action = BuildAction(
      self.identifier(), name, commands,
      input_files=input_files,
      output_files=output_files,
      optional_output_files=optional_output_files,
      files=files,
      deps=actual_deps,
      cwd=cwd,
      environ=environ,
      foreach=foreach,
      explicit=self.explicit,
      console=self.console)
    self.__actions[name] = action
    if output:
      self.__output_actions.append(action)
    return action

  def action(self, name):
    return self.__actions[name]

  def actions(self, *, outputs=False):
    """
    Returns an #utils.stream of the actions in this target. If *outputs* is
    #True, only actions marked as outputs are returned.
    """

    if outputs:
      if not self.__output_actions and self.__actions:
        result = [self.__last_action()]
      else:
        result = self.__output_actions
    else:
      result = self.__actions.values()
    return utils.stream(result)

  def __last_action(self):
    key = next(reversed(self.__actions))
    return self.__actions[key]

  def translate(self):
    if self.__is_translated:
      return
    if self.__parent:
      self.__parent.translate()
      if self.__is_translated:
        return
    for dep in self.deps(transitive=False, children=False):
      dep.translate()
    # Need to set the flag before Behaviour.translate() as when a sub-target's
    # translate() method is called within Behaviour.translate(), we will get
    # an infinite recursion.
    self.__is_translated = True
    self.impl.translate()


class DependencyList:
  """
  A helper structure that automatically establishes reverse-links in the
  #Target.dependents list when items are appended. It will also ensure that
  the list keeps a unique record of targets.
  """

  def __init__(self, target):
    self.__target = target
    self.__items = []

  def __repr__(self):
    return 'DependencyList({!r})'.format(self.__items)

  def __len__(self):
    return len(self.__items)

  def __getitem__(self, index):
    return self.__items[index]

  def __iter__(self):
    return iter(self.__items)

  def __contains__(self, item):
    return item in self.__items

  def add(self, target):
    if not isinstance(target, Target):
      msg = 'expected Target instance, got {}'
      raise TypeError(msg.format(type(target).__name__))
    if target not in self.__items:
      self.__items.append(target)
      assert self.__target not in target._Target__dependents
      target._Target__dependents.append(self.__target)
    else:
      assert self.__target in target._Target__dependents


class ChildrenList:
  """
  A helper structure that automatically establishes a reverse-link by setting
  the #Target.parent member.
  """

  def __init__(self, target):
    self.__target = target
    self.__items = []

  def __repr__(self):
    return 'ChildrenList({!r})'.format(self.__items)

  def __len__(self):
    return len(self.__items)

  def __getitem__(self, index):
    return self.__items[index]

  def __iter__(self):
    return iter(self.__items)

  def __contains__(self, item):
    return item in self.__items

  def add(self, target):
    if not isinstance(target, Target):
      msg = 'expected Target instance, got {}'
      raise TypeError(msg.format(type(target).__name__))
    if target.parent:
      raise RuntimeError('Target already has a parent')
    if target in self.__items:
      assert target.parent is self.__target
    else:
      self.__items.append(target)
      target.parent = self.__target


class Behaviour:
  """
  Implements the behaviour of a #Target.
  """

  def __init__(self, target):
    self.__target = target

  @property
  def target(self):
    return self.__target

  @property
  def namespace(self):
    return self.__target.namespace

  def __repr__(self):
    return '<{} of target {!r}>'.format(type(self).__name__, self.__target.identifier())

  def init(self, **kwargs):
    """
    This method is called when the behaviour object is created after it has
    been attached to a target and all the target's initial dependencies are
    set up.

    Note that the behaviour may generate new #Targets as the children of the
    target that the behaviour is attached to.
    """

    raise NotImplementedError

  def translate(self):
    """
    This method is called to translate the target into concrete actions, which
    are system commands to be executed in the build phase. Actions can be
    created using the #target#'s #Target.action() method.

    If multiple actions are created in a behaviour, dependencies for actions
    should be managed explicitly, otherwise the first action that is created
    will be connected to the outputs of all the targets dependencies and the
    last action created will be connected to all the inputs of all the targets
    that depend on this target (see also the #Target.action() description).
    """

    raise NotImplementedError


class Factory:
  """
  A factory wrapper for #Behaviour implementations that will automatically
  register the target in the current or specified namespace and forward all
  non-major target arguments to the #Behaviour.init() method.
  """

  def __init__(self, behaviour_class):
    self.cls = behaviour_class

  def __repr__(self):
    name = self.cls.__name__.lower().rstrip('behaviour')
    return '<{}()>'.format(name)

  def __call__(self, *, name, namespace=None, deps=None, public_deps=None,
               explicit=False, console=False, parent=None, **kwargs):
    if namespace is None:
      namespace = parent.namespace if parent else Namespace.current()
    if not namespace:
      require.breakpoint()
    target = Target(namespace, name, self.cls, explicit, console)
    for dep in (deps or ()):
      target.private_deps.add(resolve(dep))
    for dep in (public_deps or ()):
      target.public_deps.add(resolve(dep))
    if parent:
      target.parent = parent
    target.impl.init(**kwargs)
    return target

  def __instancecheck__(self, other):
    return isinstance(other, self.cls)

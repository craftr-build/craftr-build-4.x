
import collections
import re
import utils from './utils'


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
    assert isinstance(namespace, str) and len(namespace) > 0, repr(namespace)
    assert re.match('[A-z0-9@_\\-/]+', namespace), repr(namespace)
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
    self.explicit = explicit
    self.console = console

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
    return '//{}:{}'.format(self.namespace, self.long_name())

  def deps(self, transitive=False, children=True, with_behaviour=None):
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
          if children:
            yield from recursion(other.children)

    stream = utils.stream.concat(
      recursion(self.private_deps),
      recursion(self.public_deps)
    )
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
      stream = stream.concat(self.__parent.dependents(True))
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
        input=None, deps=None, output=False, cwd=None, environ=None,
        foreach=False):
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

    input_files = BuildAction.normalize_file_list(input_files or [], foreach)
    output_files = BuildAction.normalize_file_list(output_files or [], foreach)
    if foreach and len(input_files) != len(output_files):
      raise ValueError('For-each action must have the same number of input '
                       'files as output files.')

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

    if output:
      self.__output_actions.append(action)

    action = BuildAction(self.identifier(), name, commands, input_files,
        output_files, actual_deps, cwd, environ, foreach, self.explicit,
        self.console)
    self.__actions[name] = action
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

  target = utils.getter('_Behaviour__target')

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


class BuildAction:
  """
  Represents a concrete sequence of system commands.
  """

  def __init__(self, scope, name, commands, input_files, output_files, deps,
               cwd, environ, foreach, explicit, console):
    self.scope = scope
    self.name = name
    self.commands = commands
    self.input_files = input_files
    self.output_files = output_files
    self.deps = deps
    self.cwd = cwd
    self.environ = environ
    self.foreach = foreach
    self.explicit = explicit
    self.console = console

  def __repr__(self):
    return '<BuildAction {!r}>'.format(self.identifier())

  def identifier(self):
    return '{}#{}'.format(self.scope, self.name)

  @staticmethod
  def normalize_file_list(lst, foreach):
    """
    Normalizes a list of filenames, matching the format for a foreach or
    non-foreach build action. Foreach build actions use a list of lists of
    filenames, where non=foreach build actions use only list of filenames.
    """

    result = []
    for item in lst:
      if foreach:
        if isinstance(item, str):
          item = [str]
        if not isinstance(item, (list, tuple)):
          raise ValueError('expected List[^List[str]]-like, got {!r}'.format(item))
        if not all(isinstance(x, str) for x in item):
          raise ValueError('expected List[List[^str]], got {!r}'.format(item))
      else:
        if not isinstance(item, str):
          raise ValueError('expected List[^str], got {}'.format(type(item).__name__))
      result.append(item)
    return result
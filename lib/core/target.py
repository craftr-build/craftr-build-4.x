"""
Craftr's build target representation.
"""

from typing import Iterable, List
import functools
import _actions from './actions'
import it from '../utils/it'
import _session from './session'


class Cell:
  """
  A cell is a collection of build targets and usually stands as a namespace
  for a single build script.
  """

  def __init__(self, session, name, version, directory, builddir):
    if not isinstance(session, _session.Session):
      raise TypeError('session must be a Session instance')
    self.session = session
    self.name = name
    self.version = version
    self.directory = directory
    self.builddir = builddir
    self.targets = {}

  def __repr__(self):
    return '<Cell {!r}>'.format(self.name)

  def add_target(self, target):
    if target.cell is not None and target.cell is not self:
      raise RuntimeError('Target "{}" is already in cell "{}", can not '
        'add to cell "{}"'.format(target.name, target.cell.name, self.name))
    if target.name in self.targets:
      raise RuntimeError('Target "{}" already exists in Cell "{}"'
        .format(target.name, self.name))
    target.cell = self
    self.targets[target.name] = target


class Target:
  """
  A targets represents a high-level operations such as compiling source files
  and linking object files to libraries or executables. Targets can then be
  translated into #Actions (most of which will be system commands).

  The actual implementation of a target's behaviour must be implemented in a
  #TargetData subclass.

  Before the target can be used properly, it must be associated with a #Cell
  by using the #Cell.add_target() method.
  """

  def __init__(self, cell, name, private_deps, transitive_deps, data,
               explicit=False, console=False):
    if any(not isinstance(x, Target) for x in private_deps):
      raise TypeError('private_deps must be a list of Targets')
    if any(not isinstance(x, Target) for x in transitive_deps):
      raise TypeError('transitive_deps must be a list of Targets')
    if not isinstance(data, TargetData):
      raise TypeError('data must be an instance of TargetData')
    self.cell = cell
    self.name = name
    self.private_deps = private_deps
    self.transitive_deps = transitive_deps
    self.data = data
    self.explicit = explicit
    self.console = console
    self.actions = None
    data.mounted(self)

  def __repr__(self):
    return '<Target {!r}>'.format(self.long_name)

  @property
  def long_name(self):
    if self.cell is None:
      raise RuntimeError('Target is not associated with a Cell')
    return '//{}:{}'.format(self.cell.name, self.name)

  @property
  def session(self):
    return self.cell.session

  def is_translated(self):
    return self.actions is not None

  def add_action(self, action):
    """
    Adds an action to the #Target. If the action's name is not set, a free
    name will chosen automatically.
    """

    if action.target is not None and action.target is not self:
      raise RuntimeError('Action "{}" already in target "{}", can not be '
        'added to target "{}"'.format(action.name, action.target.long_name,
        self.target.long_name))
    if action.name is None:
      action.name = str(len(self.actions))
    if action.name in self.actions:
      raise RuntimeError('Action "{}" already exists in target "{}"'
        .format(action.name, self.long_name))
    action.target = self
    self.actions[action.name] = action

  def translate(self, recursive=True):
    """
    Translates the target into the action graph. All dependencies of this
    target must already be translated before it can be translated. If
    *recursive* is #True, the dependencies of the target will be translated
    automatically.
    """

    if self.is_translated():
      raise RuntimeError('Target "{}" already translated'.format(self.long_name))

    for dep in it.concat([self.private_deps, self.transitive_deps]):
      if not dep.is_translated():
        if recursive:
          dep.translate(True)
          assert dep.is_translated()
        else:
          raise RuntimeError('"{}" -> "{}" (dependent target not translated)'
            .format(self.long_name, dep.long_name))

    self.actions = {}
    self.data.translate(self)
    if not self.actions:
      _actions.Null.new(self, name=None, deps=...)

  def leaf_actions(self):
    """
    Returns all actions of the target that are leave nodes in the local
    subgraph.
    """

    actions = set(self.actions.values())
    outputs = set()
    for action in actions:
      outputs |= set(action.deps)
    return actions - outputs

  def deps(self):
    """
    Returns an iterator for all dependencies of the target that should be
    taken into account when converting the target into actions. These include
    the #deps, #transitive_deps and all transitive dependencies from those.

    This excludes all non-transitive dependencies that are not first-order
    dependencies of *self*.

    The returned iterator is a #it.stream instance. #TargetData
    implementations may find this useful due to the ability to directly access
    the #TargetData implementations they need.

    # Example

    ```python
    for d in target.deps().attr('data').of_type(MyTargetData):
      pass
    ```
    """

    def trans(target) -> Iterable[List[Target]]:
      yield target.transitive_deps
      for dep in target.transitive_deps:
        yield from trans(dep)

    def all() -> Iterable[Iterable[Target]]:
      yield self.private_deps
      yield from it.concat(trans(x) for x in self.private_deps)
      yield it.concat(trans(self))

    return it.stream(all()).concat().unique()

  def dependents(self):
    """
    Returns a list of all targets that depend on this target. Can only be used
    when the #Session.target_graph is built (thus, it can be used in
    #TargetData.translate()).
    """

    session = self.session
    if not session.target_graph:
      raise RuntimeError('Session.target_graph has not been built yet')
    return it.stream(session.target_graph[self.long_name].outputs).attr('value')


class TargetData:
  """
  Base class for the behaviour of a build target.
  """

  def __init__(self):
    self.target = None

  def mounted(self, target):
    """
    Called when the #TargetData is passed into a #Target constructor.
    """

    self.target = target

  def translate(self, target):
    """
    Called to translate the target into actions.

    # Example

    ```python
    import {ActionData, Mkdir, System} from 'craftr/core/action'
    class MyAction(ActionData):
      def translate(self, target):
        mkdir = Mkdir.new(
          target,
          name = 'mkdir',
          deps = [],
          directory=directory
        )
        System.new(
          target,
          name = 'compile',
          deps = [mkdir, ...],
          commands = commands
        )
    ```
    """

    raise NotImplementedError


def splitref(s):
  """
  Splits a target reference string into its scope and target-name component.
  A target reference must be of the format `//<scope>:<target>` or `:<target>`.
  For the latter form, the returned scope will be #None.
  """

  if not isinstance(s, str):
    raise TypeError('target-reference must be a string', s)
  if ':' not in s:
    raise ValueError('invalid target-reference string: {!r}'.format(s))
  scope, name = s.partition(':')[::2]
  if scope and not scope.startswith('//'):
    raise ValueError('invalid target-reference string: {!r}'.format(s))
  if scope:
    scope = scope[2:]
    if not scope:
      raise ValueError('invalid target-reference string: {!r}'.format(s))
  return scope or None, name


def joinref(scope, name):
  if scope:
    return '//{}:{}'.format(scope, name)
  else:
    return ':{}'.format(name)


def target_factory(target_data_class):
  """
  Returns a function that creates a new target in the current session of the
  specified *target_data_class*. The factory function accepts private and
  transitive deps not only as #Target instances but also as strings that will
  be resolved in the most-recently executed cell.
  """

  @functools.wraps(target_data_class)
  def factory(*, name, deps=(), transitive_deps=(), explicit=False,
              console=False, **kwargs):
    deps = _session.current.resolve_targets(deps)
    transitive_deps = _session.current.resolve_targets(transitive_deps)
    data = target_data_class(**kwargs)
    cell = _session.current.current_cell(create=True)
    target = Target(cell, name, deps, transitive_deps, data,
                    explicit=explicit, console=console)
    cell.add_target(target)
    return target

  return factory

"""
Craftr's build target representation.
"""

from typing import Iterable, List
import _action from './action'
import it from '../utils/it'


class Cell:
  """
  A cell is a collection of build targets and usually stands as a namespace
  for a single build script.
  """

  def __init__(self, name, version, directory, builddir):
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

  def __init__(self, cell, name, private_deps, transitive_deps, data):
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
    self.actions = None
    data.mounted(self)

  def __repr__(self):
    return '<Target {!r}>'.format(self.long_name)

  @property
  def long_name(self):
    if self.cell is None:
      raise RuntimeError('Target is not associated with a Cell')
    return '//{}:{}'.format(self.cell.name, self.name)

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

  def translate(self, recursive=True, translator=None):
    """
    Translates the target into the action graph. All dependencies of this
    target must already be translated before it can be translated. If
    *recursive* is #True, the dependencies of the target will be translated
    automatically.
    """

    if self.is_translated():
      raise RuntimeError('Target "{}" already translated'.format(self.long_name))

    for dep in it.concat(self.private_deps, self.transitive_deps):
      if not dep.is_translated():
        if recursive:
          dep.translate(True)
          assert dep.is_translated()
        else:
          raise RuntimeError('"{}" -> "{}" (dependent target not translated)'
            .format(self.long_name, dep.long_name))

    if translator_class is None:
      translator_class = Translator
    translator = translator_class(self)
    self.actions = {}
    self.data.translate(self, translator)
    if not self.actions:
      translator(None, '...', _action.Null())

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

  def translate(self, target, new_action):
    """
    Called to translate the target into actions. The *new_action* parameter
    is usually a #Translator instance which can be called to create a new
    action and associated it with the *target* immediately.

    # Example

    ```python
    import {ActionData, Mkdir, System} from 'craftr/core/action'
    class MyAction(ActionData):
      def translate(self, target, new_action):
        mkdir = new_action('mkdir', [], Mkdir(directory))
        new_action('compile', [mkdir, '...'], System(commands))
    ```
    """

    raise NotImplementedError


class Translator:
  """
  A helper class which is used in #TargetData.translate().
  """

  def __init__(self, target):
    self.target = target

  def __call__(self, name, deps, data):
    """
    Create a new action object that originates from the translator's #Target.
    The new #Action object is returned. *deps* can be the special value
    `'...'` or a list which contains the string `'...'` in which case all
    leaf actions from the target's dependencies are added.
    """

    def leaves():
      return self.target.deps().attr('leaf_actions').call().concat()

    if deps == '...':
      deps = list(leaves())
    else:
      deps = list(deps)
      try:
        index = deps.index('...')
      except ValueError:
        pass
      else:
        deps[index:index+1] = leaves()

    action = _action.Action(self.target, name, deps, data)
    self.target.add_action(action)
    return action

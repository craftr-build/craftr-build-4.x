"""
Build API.
"""

import collections
import json
import os
import craftr from './index'
import it from './utils/it'


class BuildCell:
  """
  Represents a scope for build-targets. A build-cell is created when a target
  is first declared in a Craftr build script for the script's Node.py package.
  If no package exists, the default package is `__main__`. Only the main
  build script can have no package associated.
  """

  def __init__(self, package):
    self.package = package
    self.targets = {}

  def __repr__(self):
    return '<BuildCell name={!r} directory={!r} len(targets)={}>'.format(
        self.name, self.directory, len(self.targets))

  @property
  def name(self):
    if not self.package:
      return '__main__'
    return self.package.name

  @property
  def version(self):
    if not self.package:
      return '1.0.0'
    return self.package.payload.get('version', '1.0.0')

  @property
  def directory(self):
    if not self.package:
      return str(require.main.directory)
    return str(self.package.directory)

  @property
  def build_directory(self):
    return os.path.join(craftr.build_directory, 'cells', self.name)

  def add_target(self, target):
    if target.cell is not None and target.cell is not self:
      raise RuntimeError('Target "{}" is already in cell "{}", can not '
        'add to cell "{}"'.format(target.name, target.cell.name, self.name))
    if target.name in self.targets:
      raise RuntimeError('Target "{}" already exists in Cell "{}"'
        .format(target.name, self.name))
    target.cell = self
    self.targets[target.name] = target


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


class BuildTarget:
  """
  A build-target represents a task to execute, usually to compile a set of
  source files to a library or executable. They can represent an arbitrary
  task, however, and it may consist of any number of actions.

  The behaviour of a target is implemented in a #TargetTrait. A target has a
  main trait, but traits may implement sub-traits.
  """

  def __init__(self, cell, name, internal_deps, transitive_deps, explicit, console):
    assert isinstance(cell, BuildCell)
    self.cell = cell
    self.name = name
    self.internal_deps = internal_deps
    self.transitive_deps = transitive_deps
    self.trait = None
    self.explicit = explicit
    self.console = console
    self.is_completed = False
    self.is_translated = False
    self.actions = {}

  @property
  def long_name(self):
    return '//{}:{}'.format(self.cell.name, self.name)

  def add_action(self, action):
    if not action.name:
      action.name = str(len(self.actions))
    action.target = self
    if action.name in self.actions:
      raise RuntimeError('Action "{}" already exists'.format(action.long_name))
    self.actions[action.name] = action

  def set_trait(self, trait):
    assert isinstance(trait, TargetTrait)
    self.trait = trait

  def traits(self, order='pre'):
    """
    Iterator for all traits in this target, flattened as a single iterable.
    """

    if not self.trait:
      return ()

    assert order in ('pre', 'post')
    def recursive(trait):
      if order == 'pre':
        yield trait
      for sub in trait.subtraits():
        yield sub
        recursive(sub)
      if order != 'pre':
        yield trait
    return recursive(self.trait)

  def deps(self):
    from typing import Iterable, List
    def trans(target) -> Iterable[List[BuildTarget]]:
      yield target.transitive_deps
      for dep in target.transitive_deps:
        yield from trans(dep)
    def all() -> Iterable[Iterable[BuildTarget]]:
      yield self.internal_deps
      yield from it.concat(trans(x) for x in self.internal_deps)
      yield it.concat(trans(self))
    return it.stream(all()).concat().unique()

  def complete(self):
    if self.is_completed:
      return
    for trait in self.traits(order='post'):
      trait.complete()
    self.is_completed = True

  def translate(self):
    if self.is_translated:
      return
    for trait in self.traits(order='post'):
      trait.translate()
    self.is_translated = True


class TargetTrait:
  """
  Represents behaviour of a #Target. A trait can have sub-traits. The #target
  member is already available at the time the #TargetTrait is initialized.
  """

  target = None

  @classmethod
  def new(cls, __target, *args, **kwargs):
    assert isinstance(__target, BuildTarget)
    obj = cls.__new__(cls)
    obj.target = __target
    obj.__init__(*args, **kwargs)
    return obj

  def is_main_trait(self):
    """
    Returns #True if this trait is the main trait of the target that the
    trait is associated with.
    """

    return self.target.trait is self

  def subtraits(self):
    """
    Expose sub-traits.
    """

    return ()

  def complete(self):
    """
    Finalize the information in this trait. All sub-traits are already
    completed when this method is called. This method is run before
    #translate().
    """

  def translate(self):
    """
    Translate the trait into actions by adding actions to the trait's #target.
    """

    raise NotImplementedError


class BuildAction:
  """
  Represents an actual action and system command to be performed. A
  #BuildTarget may translate into multiple build nodes.
  """

  def __init__(self, target=None, name=None, deps=None, commands=None,
               input_files=None, output_files=None, cwd=None, environ=None):
    self.target = target
    self.name = name
    self.deps = deps
    self.commands = commands or []
    self.input_files = input_files or []
    self.output_files = output_files or []
    self.cwd = cwd
    self.environ = environ

  def __repr__(self):
    return '<BuildTarget "{}">'.format(self.long_name)

  @property
  def long_name(self):
    tname = '<unbound>' if not self.target else self.target.long_name
    return '{}#{}'.format(tname, self.name)


class BuildGraph:

  BuildNode = collections.namedtuple('BuildNode', 'name deps commands input_files output_files cwd environ explicit console')

  def __init__(self):
    self.nodes = {}

  def from_actions(self, actions):
    for action in actions:
      node = self.BuildNode(
          action.long_name, [x.long_name for x in action.deps],
          action.commands, action.input_files, action.output_files,
          action.cwd, action.environ, action.target.explicit,
          action.target.console)
      self.nodes[node.name] = node
    return self

  def from_json(self, data):
    self.nodes.update({x['name']: self.BuildNode(**x) for x in data})

  def to_json(self):
    return [x._asdict() for x in self.nodes.values()]

  def read(self, filename):
    with open(filename, 'r') as fp:
      self.from_json(json.load(fp))

  def write(self, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as fp:
      json.dump(self.to_json(), fp)

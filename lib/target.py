"""
Craftr's build target representation.
"""

from typing import Iterable, List
import it from './utils/it'


class Cell:
  """
  A cell is a collection of build targets and usually stands as a namespace
  for a single build script.
  """

  def __init__(self, name):
    self.name = name
    self.targets = {}

  def __repr__(self):
    return '<Cell {!r}>'.format(self.name)


class Target:
  """
  A targets represents a high-level operations such as compiling source files
  and linking object files to libraries or executables. Targets can then be
  translated into #Actions (most of which will be system commands).

  The actual implementation of a target's behaviour must be implemented in a
  #TargetData subclass.
  """

  def __init__(self, cell, name, private_deps, transitive_deps, data):
    if not isinstance(cell, Cell):
      raise TypeError('cell must be an instance of Cell')
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
    data.mounted(self)

  def __repr__(self):
    return '<Target {!r}>'.format(self.long_name)

  @property
  def long_name(self):
    return '//{}:{}'.format(self.cell.name, self.name)

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

  def translate(self, target):
    """
    Called to translate the target into actions.
    """

    raise NotImplementedError

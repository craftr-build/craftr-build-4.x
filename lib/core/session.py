"""
The Craftr session contains all the global information on the current build
process, including configuration values and all build cells with the target
definitions from loaded build scripts.
"""

import os
import traceback
import werkzeug.local as _local
import _target from './target'
import _actions from './actions'
import graph from '../utils/graph'
import cfg from '../utils/cfg'


class BaseGraph(graph.Graph):
  """
  Base class for the #TargetGraph and #ActionGraph classes.
  """

  def _get_deps_for(self, obj):
    if isinstance(obj, _target.Target):
      return list(obj.private_deps) + list(obj.transitive_deps)
    elif isinstance(obj, _actions.Action):
      return list(obj.deps)
    else:
      raise RuntimeError('unsupported object in BaseGraph._get_deps_for(): {}'
        .format(type(obj).__name__))

  def _get_key_for(self, obj):
    return obj.long_name

  @classmethod
  def from_(cls, objects):
    g = cls()
    for obj in objects:
      g.add(obj)
    return g

  def add(self, obj, recursive=True):
    try:
      node = self[self._get_key_for(obj)]
      assert node.value is obj, (node.value, obj)
      return node
    except KeyError:
      node = graph.Node(self._get_key_for(obj), obj)
      super().add(node)

    if recursive:
      for dep in self._get_deps_for(obj):
        other = self.add(dep, True)
        other.connect(node)
    return node

  def remove(self, obj):
    node = self[self._get_key_for(obj)]
    super().remove(node)

  def topo_sort(self):
    for node in super().topo_sort():
      yield node.value

  def values(self):
    return (node.value for node in self.nodes())


class TargetGraph(BaseGraph):

  def translate(self, targets=None):
    # Default to all non-explicit targets.
    if targets is None:
      targets = [x for x in self.values() if not x.explicit]

    # Ensure that all targets are translated into actions.
    for target in self.topo_sort():
      if not target.is_translated():
        target.translate(recursive=False)

    # Build up the action graph.
    g = ActionGraph()
    for target in targets:
      for action in target.actions.values():
        g.add(action)

    return g


class ActionGraph(BaseGraph):
  pass


class Session:

  current = None
  EVENTS = ('after_load',)

  def __init__(self, projectdir=None, builddir=None):
    self.builddir = builddir or 'build'
    self.projectdir = projectdir or os.getcwd()
    self.config = cfg.Configuration()
    self.cells = {}
    self.listeners = {}

  def __enter__(self):
    if Session.current:
      raise RuntimeError('a nested Session context is not supported')
    Session.current = self
    return self

  def __exit__(self, *args):
    Session.current = None

  def on(self, event_name, handler):
    if event_name not in self.EVENTS:
      raise ValueError('unknown event type: {!r}'.format(event_name))
    self.listeners.setdefault(event_name, []).append(handler)

  def trigger_event(self, event_name):
    if event_name not in self.EVENTS:
      raise ValueError('unknown event type: {!r}'.format(event_name))
    for handler in self.listeners.get(event_name, []):
      try:
        handler()
      except:
        traceback.print_exc()

  def current_cell(self, create=False):
    """
    Returns the #_target.Cell that is currently being executed. If *create*
    is #True and the current cell does not yet exist, it will be created.
    """

    for module in require.context.module_stack:
      if module == require.main and not module.package:
        name = '__main__'
        version = '1.0.0'
        directory = module.directory
      elif not module.package:
        continue
      else:
        name = module.package.name
        version = module.package.payload.get('version', '1.0.0')
        directory = module.package.directory
      cell = self.cells.get(name)
      if not cell and create:
        cell = _target.Cell(self, name, version, directory, self.builddir_for(name))
        self.cells[name] = cell
      if cell:
        return cell
    raise RuntimeError('no active cell found')

  def builddir_for(self, module_name):
    return os.path.join(self.builddir, 'cells', module_name)

  def resolve_target(self, target):
    if isinstance(target, _target.Target):
      return target
    scope, name = _target.splitref(target)
    if not scope:
      scope = self.current_cell().name
    try:
      return self.cells[scope].targets[name]
    except KeyError:
      raise ValueError('scope or target does not exist: {!r}'.format(
        _target.joinref(scope, name)))

  def resolve_targets(self, targets):
    """
    Resolves all target-reference strings in *targets* to actual targets. The
    list may also contain actual target objects.
    """

    return [self.resolve_target(x) for x in targets]

  def build_target_graph(self):
    """
    Builds a #graph.Graph from the registered targets.
    """

    g = TargetGraph()
    for cell in self.cells.values():
      for target in cell.targets.values():
        g.add(target)
    return g


@_local.LocalProxy
def current():
  if not Session.current:
    raise RuntimeError('no active session')
  return Session.current

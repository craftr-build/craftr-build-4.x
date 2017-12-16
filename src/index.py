"""
Public build-script API of the Craftr build system.
"""

import {Configuration} from './utils/cfgparser'
import path from './utils/path'

#: Set to True when this is a release build.
release = False

#: Set to the build directory.
build_directory = None

#: This is a persistent cache that is serialized into JSON. All objects in
#: this dictionary must be JSON serializable.
cache = {}

#: Craftr configuration, automatically loaded from the configuration file
#: by the CLI.
options = Configuration()

#: The cells that have been created during the execution of the build script.
cells = {}


import _build, {BuildCell, BuildAction,
                BuildTarget, TargetTrait, BuildGraph}
    from './build'


def current_cell(create=False):
  """
  Retrieves the current #BuildCell. If there is no current cell, a
  #RuntimeError is raised, unless *create* is set to #True, in which case
  a new #BuildCell will be created.
  """

  cell = BuildCell(require.current.package)
  if not cell.package and require.current != require.main:
    if create:
      raise RuntimeError('can not create BuildCell for non-main script '
                         'without an associated Node.py package')
    return None

  if create:
    return cells.setdefault(cell.name, cell)
  else:
    try:
      return cells[cell.name]
    except KeyError:
      raise RuntimeError('no active BuildCell')


def resolve_target(target):
  """
  Resolve a target identifier string of the format `[//<cell>]:target`.
  If *target* is already a #BuildTarget instance, it is returned as-is.
  """

  if isinstance(target, BuildTarget):
    return target
  cell_name, name = _build.splitref(target)
  if not cell_name:
    cell_name = current_cell().name
  try:
    return cells[cell_name].targets[name]
  except KeyError:
    raise ValueError('cell or target does not exist: {!r}'.format(
      _build.joinref(cell_name, name)))


def localpath(p):
  """
  Returns the canonical representation of the path *p*. If *p* is a relative
  path, it will be considered relative to the current module's directory.
  """

  if path.isrel(p):
    p = path.join(str(require.current.directory), p)
  return path.canonical(p)


def glob(patterns, parent=None, excludes=None):
  """
  Same as #path.glob(), except that *parent* defaults to the parent directory
  of the currently executed module (not always the same directory as the cell
  base directory!).
  """

  if not parent:
    parent = str(require.current.directory)
  return path.glob(patterns, parent, excludes)


class TargetFactory(object):

  def __init__(self, cls):
    assert issubclass(cls, TargetTrait)
    self.cls = cls
    self.preprocessors = []
    self.postprocessors = []

  def __repr__(self):
    return '<target_factory data_class={!r}>'.format(self.cls)

  def __call__(self,*, name, deps=(), transitive_deps=(), explicit=False,
              console=False, **kwargs):
    for func in self.preprocessors:
      func(kwargs)
    cell = current_cell(create=True)
    deps = [resolve_target(x) for x in deps]
    transitive_deps = [resolve_target(x) for x in transitive_deps]
    target = BuildTarget(cell, name, deps, transitive_deps, explicit, console)
    target.set_trait(self.cls.new(target, **kwargs))
    cell.add_target(target)
    for func in self.postprocessors:
      func(target)
    return target

  def __instancecheck__(self, other):
    return isinstance(other, self.cls)

  def preprocess(self, func):
    self.preprocessors.append(func)
    return func

  def postprocessors(self, func):
    self.postprocessors.append(func)
    return func


@TargetFactory
class gentarget(TargetTrait):

  def __init__(self, commands, environ=None, cwd=None, input_files=(), output_files=()):
    self.commands = commands
    self.environ = environ
    self.cwd = cwd
    self.input_files = input_files
    self.output_files = output_files

  def add_additional_args(self, args):
    """
    The default build backend calls this function when additional command-line
    arguments are specified for this specific target.
    """

    self.commands[-1].extend(args)

  def translate(self):
    self.target.add_action(BuildAction(
      deps=..., commands=self.commands,
      cwd=self.cwd, environ=self.environ,
      input_files=self.input_files, output_files=self.output_files))

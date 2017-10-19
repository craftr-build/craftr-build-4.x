"""
The public API when importing the `craftr` package.
"""

import fnmatch as _fnmatch
import functools
import {Action, ActionData} from './core/action'
import {Cell, Target, TargetData} from './core/target'
import _target from './core/target'
import path from './utils/path'
import config from './config'
import platform from './platform'

builddir = 'build'
target = platform.Triplet.current()
cells = {}


def current_cell():
  """
  Returns the currently executed build cell. If there is not already a cell
  for the currently executed Node.py module, a new cell will be created.
  Cells can only be created for modules inside a package. All modules inside
  the same package will be part of the same cell.
  """

  package = require.current.package
  if not package:
    raise RuntimeError('module {!r} is not in a package'.format(require.current))
  if package.name not in cells:
    bdir = path.join(builddir, 'cells', package.name)
    version = package.payload['package'].get('version', '1.0.0')
    cells[package.name] = Cell(package.name, version, package.directory, bdir)
  return cells[package.name]


def find_target(name):
  """
  Resolves a target name in the current cell (relative identifier) or in the
  #cells dictionary (absolute identifier).
  """

  if name.startswith(':'):
    cell, name = None, name[1:]
  elif name.startswith('//'):
    cell, name = name[2:].partition(':')[::2]
  else:
    raise ValueError('invalid target identifier: {!r}'.format(name))

  if cell is None:
    cell = current_cell()
  else:
    cell = cells[name]

  return cell.targets[name]


def target_factory(target_data_type):
  """
  Returns a function that creates a new target into the current cell and
  returns it.
  """

  def resolve_deps(deps):
    return [find_target(x) if isinstance(x, str) else x for x in deps]

  @functools.wraps(target_data_type)
  def wrapper(*, name, deps=(), transitive_deps=(), **kwargs):
    cell = current_cell()
    private_deps = resolve_deps(deps)
    transitive_deps = resolve_deps(transitive_deps)
    data = target_data_type(**kwargs)
    target = Target(cell, name, private_deps, transitive_deps, data)
    cell.add_target(target)
    return target

  return wrapper


def glob(patterns, parent=None, excludes=None):
  """
  Same as #path.glob(), except that *parent* defaults to the parent directory
  of the currently executed module (not always the same directory as the cell
  base directory!).
  """

  if not parent:
    parent = require.current.directory
  return path.glob(patterns, parent, excludes)


def match(string, matchers, kind='glob', default=NotImplemented):
  """
  Matches the specified *string* against a dictionary of patterns and returns
  the first matching value. If *matchers* is just a string, it is considered
  a single pattern and the function returns True or False, depending on
  whether the pattern matches the *string*. Otherwise, it must be a dictionary
  where every key is a pattern, and the value is returned if the pattern
  matches.

  # Parameters
  string (str): The string to match.
  matchers (str, dict): The pattern or patterns to match.
  kind (str): Either `'glob'` or `'regex'`.
  default (any): If *matchers* is a dictionary, the default value to return
    when no pattern matched. When no pattern matched, it tries to determine
    the default value by using the type of the values in *matchers*. If they
    are no all of the same type, the deduction fails and a #ValueError is
    raised.

  # Example
  ```python
  import {match, target} from 'craftr'

  text = match(target, {
    'x86-*-win*': 'x86 Windows',
    'x86_64-*-win*': 'x64 Windows',
    '*-linux*': 'Linux'
  })

  if match(target, 'x86*'):
    # ...
  ```
  """

  string = str(string)

  assert kind in ('regex', 'glob')
  if isinstance(matchers, str):
    if kind == 'glob':
      return _fnmatch.fnmatch(string, matchers)
    else:
      return re.match(matchers, string, re.I) is not None

  default_type = NotImplemented
  for key, value in matchers.items():
    if default_type is NotImplemented:
      default_type = type(value)
    elif default_type is not None and type(value) != default_type:
      default_type = None
    if kind == 'glob' and _fnmatch.fnmatch(string, key):
      return value
    elif kind == 'regex' and re.match(key, string, re.I) is not None:
      return value

  if default is NotImplemented:
    if default_type in (NotImplemented, None):
      raise ValueError('no patterns matched, default return value could '
        'be determined.')
    default = default_type()
  return default

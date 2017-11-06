"""
The public API when importing the `craftr` package.
"""

import fnmatch as _fnmatch
import path from './utils/path'
import actions from './core/actions'
import target, {target_factory} from './core/target'
import {Session, current as session} from './core/session'


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

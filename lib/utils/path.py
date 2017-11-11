"""
Replacement for #os.path with more functionality and a concise API.
"""

import functools
import glob2
import operator
import os
import stat
import typing as t

from os import (
  sep,
  pathsep,
  curdir,
  pardir,
  getcwd as cwd
)
from os.path import (
  expanduser,
  normpath as norm,
  isabs,
  isfile,
  isdir,
  exists,
  join,
  split,
  dirname as dir,
  basename as base
)


def canonical(path: str, parent: str = None):
  return norm(abs(path, parent))


def abs(path: str, parent: str = None) -> str:
  if not isabs(path):
    return join(parent or cwd(), path)
  return path


def rel(path: str, parent: str = None, par: bool = False) -> str:
  """
  Takes *path* and computes the relative path from *parent*. If *parent* is
  omitted, the current working directory is used.

  If *par* is #True, a relative path is always created when possible.
  Otherwise, a relative path is only returned if *path* lives inside the
  *parent* directory.
  """

  try:
    res = os.path.relpath(path, parent)
  except ValueError:
    # Raised eg. on Windows for differing drive letters.
    if not par:
      return abs(path)
    raise
  else:
    if not issub(res):
      return abs(path)
    return res


def isrel(path: str) -> bool:
  return not isabs(path)


def issub(path: str) -> bool:
  """
  Returns #True if *path* is a relative path that does not point outside
  of its parent directory or is equal to its parent directory (thus, this
  function will also return False for a path like `./`).
  """

  if isabs(path):
    return False
  if path.startswith(curdir + sep) or path.startswith(pardir + sep):
    return False
  return True


def isglob(path):
  """
  # Parameters
  path (str): The string to check whether it represents a glob-pattern.

  # Returns
  #True if the path is a glob pattern, #False otherwise.
  """

  return '*' in path or '?' in path


def glob(patterns: t.Union[str, t.List[str]], parent: str = None,
         excludes: t.List[str] = None, include_dotfiles: bool = False,
         ignore_false_excludes: bool = False) -> t.List[str]:
  """
  Wrapper for #glob2.glob() that accepts an arbitrary number of
  patterns and matches them. The paths are normalized with #norm().

  Relative patterns are automaticlly joined with *parent*. If the
  parameter is omitted, it defaults to the current working directory.

  If *excludes* is specified, it must be a string or a list of strings
  that is/contains glob patterns or filenames to be removed from the
  result before returning.

  > Every file listed in *excludes* will only remove **one** match from
  > the result list that was generated from *patterns*. Thus, if you
  > want to exclude some files with a pattern except for a specific file
  > that would also match that pattern, simply list that file another
  > time in the *patterns*.

  # Parameters
  patterns (list of str): A list of glob patterns or filenames.
  parent (str): The parent directory for relative paths.
  excludes (list of str): A list of glob patterns or filenames.
  include_dotfiles (bool): If True, `*` and `**` can also capture
    file or directory names starting with a dot.
  ignore_false_excludes (bool): False by default. If True, items listed
    in *excludes* that have not been globbed will raise an exception.

  # Returns
  list of str: A list of filenames.
  """

  if isinstance(patterns, str):
    patterns = [patterns]

  if not parent:
    parent = cwd()

  result = []
  for pattern in patterns:
    if not isabs(pattern):
      pattern = join(parent, pattern)
    result += glob2.glob(canonical(pattern))

  for pattern in (excludes or ()):
    if not isabs(pattern):
      pattern = join(parent, pattern)
    pattern = canonical(pattern)
    if not isglob(pattern):
      try:
        result.remove(pattern)
      except ValueError as exc:
        if not ignore_false_excludes:
          raise ValueError('{} ({})'.format(exc, pattern))
    else:
      for item in glob2.glob(pattern):
        try:
          result.remove(item)
        except ValueError as exc:
          if not ignore_false_excludes:
            raise ValueError('{} ({})'.format(exc, pattern))

  return result


def addtobase(subject, base_suffix):
  """
  Adds the string *base_suffix* to the basename of *subject*.
  """

  if not base_suffix:
    return subject
  base, ext = os.path.splitext(subject)
  return base + base_suffix + ext


def addprefix(subject, prefix):
  """
  Adds the specified *prefix* to the last path element in *subject*.
  If *prefix* is a callable, it must accept exactly one argument, which
  is the last path element, and return a modified value.
  """

  if not prefix:
    return subject
  dir_, base = split(subject)
  if callable(prefix):
    base = prefix(base)
  else:
    base = prefix + base
  return join(dir_, base)


def addsuffix(subject, suffix, replace=False):
  """
  Adds the specified *suffix* to the *subject*. If *replace* is True, the
  old suffix will be removed first. If *suffix* is callable, it must accept
  exactly one argument and return a modified value.
  """

  if not suffix and not replace:
    return subject
  if replace:
    subject = rmvsuffix(subject)
  if suffix and callable(suffix):
    subject = suffix(subject)
  elif suffix:
    subject += suffix
  return subject


def setsuffix(subject, suffix):
  """
  Synonymous for passing the True for the *replace* parameter in #addsuffix().
  """

  return addsuffix(subject, suffix, replace=True)


def rmvsuffix(subject):
  """
  Remove the suffix from *subject*.
  """

  index = subject.rfind('.')
  if index > subject.replace('\\', '/').rfind('/'):
    subject = subject[:index]
  return subject


def getsuffix(subject):
  """
  Returns the suffix of a filename. If the file has no suffix, returns None.
  Can return an empty string if the filenam ends with a period.
  """

  index = subject.rfind('.')
  if index > subject.replace('\\', '/').rfind('/'):
    return subject[index+1:]
  return None


def makedirs(path, exist_ok=True):
  """
  Like #os.makedirs(), with *exist_ok* defaulting to #True.
  """

  os.makedirs(path, exist_ok=exist_ok)


def chmod_update(flags, modstring):
  """
  Modifies *flags* according to *modstring*.
  """

  mapping = {
    'r': (stat.S_IRUSR, stat.S_IRGRP, stat.S_IROTH),
    'w': (stat.S_IWUSR, stat.S_IWGRP, stat.S_IWOTH),
    'x': (stat.S_IXUSR, stat.S_IXGRP, stat.S_IXOTH)
  }

  target, direction = 'a', None
  for c in modstring:
    if c in '+-':
      direction = c
      continue
    if c in 'ugoa':
      target = c
      direction = None  # Need a - or + after group specifier.
      continue
    if c in 'rwx' and direction in '+-':
      if target == 'a':
        mask = functools.reduce(operator.or_, mapping[c])
      else:
        mask = mapping[c]['ugo'.index(target)]
      if direction == '-':
        flags &= ~mask
      else:
        flags |= mask
      continue
    raise ValueError('invalid chmod: {!r}'.format(modstring))

  return flags


def chmod_repr(flags):
  """
  Returns a string representation of the access flags *flags*.
  """

  template = 'rwxrwxrwx'
  order = (stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR,
           stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP,
           stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH)
  return ''.join(template[i] if flags&x else '-'
                 for i, x in enumerate(order))


def chmod(path, modstring):
  flags = chmod_update(os.stat(path).st_mode, modstring)
  os.chmod(path, flags)

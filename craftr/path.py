
import os
import glob2


def canonical(path, parent=None):
  if not os.path.isabs(path):
    if parent:
      path = os.path.join(parent, path)
    path = os.path.abspath(path)
  return os.path.normpath(path)


def isglob(path):
  """
  Checks if *path* is a glob pattern. Returns #True if it is, #False if not.
  """

  return '*' in path or '?' in path


def glob(patterns, parent=None, excludes=None, include_dotfiles=False,
         ignore_false_excludes=False):
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
    parent = os.getcwd()

  result = []
  for pattern in patterns:
    if not os.path.isabs(pattern):
      pattern = os.path.join(parent, pattern)
    result += glob2.glob(canonical(pattern))

  for pattern in (excludes or ()):
    if not os.path.isabs(pattern):
      pattern = os.path.join(parent, pattern)
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

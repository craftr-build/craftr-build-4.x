
import re
import os

def quote(s, for_ninja=False):
  """
  Enhanced implementation of :func:`shlex.quote` as it generates single-quotes
  on Windows which can lead to problems.
  """

  if os.name == 'nt' and os.sep == '\\':
    s = s.replace('"', '\\"')
    if re.search('\s', s) or any(c in s for c in '<>'):
      s = '"' + s + '"'
  else:
    s = shlex.quote(s)
  if for_ninja:
    # Fix escaped $ variables on Unix, see issue craftr-build/craftr#30
    s = re.sub(r"'(\$\w+)'", r'\1', s)
  return s

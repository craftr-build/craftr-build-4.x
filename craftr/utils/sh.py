# The MIT License (MIT)
#
# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import contextlib
import os
import re
import shlex

from shutil import which
from subprocess import PIPE, STDOUT, call, check_call, check_output, CalledProcessError


class safe(str):
  """
  Wrapping a string in this subclass of #str will cause it not to be escaped
  when passed to #quote().
  """


def split(s):
  """
  Enhanced implementation of :func:`shlex.split`.
  """

  result = shlex.split(s, posix=(os.name != 'nt'))
  if os.name == 'nt':
    # With posix=False, shlex.split() will not interpret \ as the
    # escape character (which is what we need on windows), but it
    # will also not eliminate quotes, which is what we need to do
    # here now.
    quotes = '\"\''
    result = [x[1:-1] if (x and x[0] in quotes and x[-1] in quotes) else x for x in result]
  return result


def quote(s, for_ninja=False):
  """
  Enhanced implementation of #shlex.quote() as it generates single-quotes
  on Windows which can lead to problems.
  """

  if isinstance(s, safe):
    return s
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


def join(args):
  return ' '.join(map(quote, args))


def shellify(args):
  if os.name == 'nt':
    return ['cmd.exe', '/c', join(args)]
  return [os.getenv('SHELL', 'sh'), '-c', join(args)]


@contextlib.contextmanager
def override_environ(environ):
  old = os.environ.copy()
  os.environ.update(environ)
  try:
    yield
  finally:
    os.environ.update(old)
    for key in environ:
      if key not in old:
        del os.environ[key]

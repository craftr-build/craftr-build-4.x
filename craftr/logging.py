# Copyright (C) 2015  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from craftr import session, module, ModuleError
from craftr import tty

import sys


# Log-level metadata about the minimum required verbosity level for
# printing a stack-trace and the colors for colorized output.
LOG_METADATA = {
  'info':  {'strace_min_verbosity': 2, 'fg': tty.compile('CYAN', attrs='BRIGHT')},
  'warn':  {'strace_min_verbosity': 2, 'fg': tty.compile('MAGENTA', attrs='BRIGHT')},
  'error': {'strace_min_verbosity': 1, 'fg': tty.compile(fg='RED', attrs='BRIGHT')},
}


def _log(level, *args, **kwargs):
  meta = LOG_METADATA[level]
  prefix = meta['fg'] + 'craftr|{0:>5}'.format(level)
  if module:
    prefix += '|' + module.project_name
  prefix += ' -> ' + tty.reset
  kwargs.setdefault('file', sys.stderr)
  end = kwargs.pop('end', '\n')
  kwargs['file'].write(prefix)
  print(*args, end='', **kwargs)
  kwargs['file'].write(tty.reset)
  kwargs['file'].write(end)


def info(*args, **kwargs):
  return _log('info', *args, **kwargs)


def warn(*args, **kwargs):
  return _log('warn', *args, **kwargs)


def error(*args, **kwargs):
  try:
    return _log('error', *args, **kwargs)
  finally:
    if module:
      raise ModuleError()

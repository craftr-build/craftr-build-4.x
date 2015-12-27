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
from craftr import magic, path, tty

import sys
import traceback


# Log-level metadata about the minimum required verbosity level for
# printing a stack-trace and the colors for colorized output.
LOG_METADATA = {
  'info':  {'strace_min_verbosity': 2, 'fg': tty.compile('cyan', attrs='bold')},
  'warn':  {'strace_min_verbosity': 2, 'fg': tty.compile('magenta', attrs='bold')},
  'error': {'strace_min_verbosity': 1, 'fg': tty.compile('red', attrs='bold')},
}


def _walk_frames(start_frame=None, stacklevel=1, max_frames=0):
  if start_frame is None:
    start_frame = magic.get_frame(stacklevel)
  frame = start_frame
  count = 0
  while frame and (max_frames == 0 or count < max_frames):
    yield frame
    frame = frame.f_back
    count += 1


def _log(level, *args, stacklevel=1, **kwargs):
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
  if session and module and session.verbosity >= meta['strace_min_verbosity']:
    max_frames = session.strace_depth
    frames = list(_walk_frames(stacklevel=(stacklevel + 1), max_frames=max_frames))
    for frame in reversed(frames):
      fn = frame.f_code.co_filename
      if fn.startswith('<'):
        fn = tty.colored(fn, 'yellow')
      else:
        fn = path.relpath(fn)
        fn = tty.colored(fn, 'blue')
      func = frame.f_code.co_name
      lineno = frame.f_lineno
      if func.startswith('<'):
        func = tty.colored(func, 'yellow', attrs='bold')
      else:
        func = tty.colored(func + '()', 'blue', attrs='bold')
      print('  In', func, '[{0}:{1}]'.format(fn, lineno))


def info(*args, stacklevel=1, **kwargs):
  _log('info', *args, stacklevel=(stacklevel + 1), **kwargs)


def warn(*args, stacklevel=1, **kwargs):
  _log('warn', *args, stacklevel=(stacklevel + 1), **kwargs)


def error(*args, stacklevel=1, **kwargs):
  _log('error', *args, stacklevel=(stacklevel + 1), **kwargs)
  if module:
    raise ModuleError()

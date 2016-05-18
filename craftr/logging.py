# Copyright (C) 2016  Niklas Rosenstein
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
  'debug': {'strace_min_verbosity': 3, 'fg': tty.compile('grey', attrs='bold')},
  'info':  {'strace_min_verbosity': 2, 'fg': tty.compile('white')},
  'warn':  {'strace_min_verbosity': 2, 'fg': tty.compile('magenta')},
  'error': {'strace_min_verbosity': 1, 'fg': tty.compile('red', attrs='bold')},
}


def _walk_frames(start_frame=None, stacklevel=1, max_frames=0, skip_builtins=True):
  if start_frame is None:
    start_frame = magic.get_frame(stacklevel)
  frame = start_frame
  count = 0
  while frame and (max_frames == 0 or count < max_frames):
    if skip_builtins and frame.f_code.co_filename.startswith('<'):
      pass
    else:
      yield frame
      count += 1
    frame = frame.f_back


def debug(*args, stacklevel=1, verbosity=None, **kwargs):
  if verbosity is None and session:
    verbosity = session.verbosity
  if verbosity is None or verbosity >= 1:
    stacklevel += 1
    log('debug', *args, stacklevel=stacklevel, **kwargs)


def log(level, *args, stacklevel=1, module_name=None, show_trace=None, **kwargs):
  levelinfo = LOG_METADATA[level]
  prefix = levelinfo['fg']
  if not module_name and module:
    module_name = module.project_name
  if module_name and session.verbosity > 0:
    prefix += '(craftr.ext.' + module_name
    if module:
      prefix += ', line ' + str(magic.get_module_frame(module).f_lineno)
    prefix += '): '

  end = kwargs.pop('end', '\n')
  file = kwargs.pop('file', sys.stderr)
  file.write(prefix)
  print(*args, end='', file=file, **kwargs)
  file.write(tty.reset)
  file.write(end)

  if show_trace is None:
    show_trace = bool(session and module and session.verbosity >= levelinfo['strace_min_verbosity'])
  if show_trace:
    max_frames = session.strace_depth
    frames = list(_walk_frames(stacklevel=(stacklevel + 1), max_frames=max_frames))
    for frame in reversed(frames):
      fn = frame.f_code.co_filename
      if not fn.startswith('<'):  # not built-in module filename
        fn = path.relpath(fn, session.cwd, only_sub=True)
      fn = tty.colored(fn, 'red', attrs='bold')

      func = frame.f_code.co_name
      if func == '<module>' and 'project_name' in frame.f_globals:
        func = '<craftr.ext.{0}>'.format(frame.f_globals['project_name'])
      if func.startswith('<'):
        func = tty.colored(func, 'blue', attrs='bold')
      else:
        func = tty.colored(func + '()', 'blue', attrs='bold')

      lineno = frame.f_lineno
      print('  In', func, '({0}, line {1})'.format(fn, lineno), file=file)


def info(*args, stacklevel=1, **kwargs):
  stacklevel += 1
  log('info', *args, stacklevel=stacklevel, **kwargs)


def warn(*args, stacklevel=1, **kwargs):
  stacklevel += 1
  log('warn', *args, stacklevel=stacklevel, **kwargs)


def error(*args, stacklevel=1, raise_=True, **kwargs):
  stacklevel += 1
  log('error', *args, stacklevel=stacklevel, **kwargs)
  if raise_ and module:
    raise ModuleError()

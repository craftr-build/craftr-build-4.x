# Copyright (C) 2015 Niklas Rosenstein
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

import os
import sys
import textwrap

try:
  import colorama
except ImportError:
  colorama = None
else:
  colorama.init()

get_stdout = lambda: sys.stdout
get_stderr = lambda: sys.stderr


DEBUG = 10
INFO = 20
WARNING = 30
ERROR = 40
CRITICAL = 50

levels = {
  DEBUG: 'DEBUG',
  INFO: 'INFO',
  WARNING: 'WARNING',
  ERROR: 'ERROR',
  CRITICAL: 'CRITICAL',
}

# Terminal styles for the logging output.
styles = {
  DEBUG: ('YELLOW', None, None),
  INFO: ('CYAN', None, None),
  WARNING: ('MAGENTA', None, None),
  ERROR: ('RED', None, 'BRIGHT'),
  CRITICAL: ('WHITE', 'RED', 'BRIGHT'),
}


def get_level_name(level):
  try:
    return levels[level]
  except KeyError:
    return 'Level {}'.format(level)


def get_level_style(level):
  if not colorama:
    return ('', '')
  try:
    fg, bg, attr = styles[level]
  except KeyError:
    return ('', '')

  prefix = ''
  if fg:
    prefix += getattr(colorama.Fore, fg)
  if bg:
    prefix += getattr(colorama.Back, bg)
  if attr:
    prefix += getattr(colorama.Style, attr)
  return (prefix, colorama.Style.RESET_ALL)


def wrap_text(text, width, initial_width=None):
  ''' Better suited text wrapping than `textwrap.TextWrapper()`, I
  couldn't get it to do what this function will do. '''

  if initial_width is None:
    initial_width = width

  lines = text.split('\n')
  index = 0
  while index < len(lines):
    lines[index] = lines[index].rstrip('\n')
    if (index == 0 and len(lines[index]) >= initial_width) or \
        (len(lines[index]) >= width):
      newlines = textwrap.wrap(lines[index], initial_width if index == 0 else width)
      if len(newlines) > 2:
        newlines[1:] = [' '.join(line for line in newlines[1:])]
      lines[index:index+1] = newlines
    index += 1

  if lines and not lines[-1]:
    lines.pop()
  return lines


def emit(prefix, message, level, fp=None, frame=None):
  ''' Emit the *message* with the specified *prefix* to the file-like
  object *fp*. If `fp.isatty()` returns True and if the `colorama`
  module is available, the output will be colorized. The prefix may
  contain a `{levelname}` format string which will automatically be
  substituted. '''

  fp = fp or get_stdout()

  fmtargs = {'levelname': get_level_name(level), 'lineno': None, 'fn': None}
  if frame:
    fmtargs['lineno'] = frame.f_lineno
    fmtargs['fn'] = os.path.basename(frame.f_code.co_filename)

  prefix = str(prefix).format(**fmtargs)
  if hasattr(fp, 'isatty') and fp.isatty():
    style = get_level_style(level)
  else:
    style = ('', '')

  width = terminal_size()[0] - 1
  prefix_len = len(prefix) + 1
  lines = wrap_text(message, width, width - prefix_len)

  fp.write(style[0])
  fp.write(prefix)
  fp.write(lines[0])
  fp.write('\n')
  for line in lines[1:]:
    fp.write('  ' + line + '\n')
  fp.write(style[1])


def print_as_str(*objects, sep=' ', end='\n'):
  ''' Takes arguments to the `print()` function and returns a string
  the way it would be printed to the output file. '''

  return sep.join(str(x) for x in objects) + end


def terminal_size():
  ''' Determines the size of the terminal. '''

  if os.name == 'nt':
    # http://code.activestate.com/recipes/440694-determine-size-of-console-window-on-windows/
    import ctypes, struct
    h = ctypes.windll.kernel32.GetStdHandle(-12)
    csbi = ctypes.create_string_buffer(22)
    res = ctypes.windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
    if res:
      (bufx, bufy, curx, cury, wattr, left, top, right,
       bottom, maxx, maxy) = struct.unpack('hhhhHhhhhhh', csbi.raw)
      sizex = right - left + 1
      sizey = bottom - top + 1
    else:
      sizex, sizey = 80, 25
    return (sizex, sizey)
  else:
    # http://stackoverflow.com/a/3010495/791713
    import fcntl, termios, struct
    h, w, hp, wp = struct.unpack('HHHH',
        fcntl.ioctl(0, termios.TIOCGWINSZ,
        struct.pack('HHHH', 0, 0, 0, 0)))
    return w, h


def clear_line():
  ''' Clear the current line in the terminal with whitespace and reset
  the cursor to the start of the line. '''

  # XXX: Is there an ANSI escape sequence to clear the current line?
  width = terminal_size()[0]
  print('\r' + ' ' * (width - 1), end='\r')


class Logger(object):
  ''' Simple logger class. '''

  def __init__(self, prefix=None, level=0):
    super().__init__()
    self.prefix = prefix or ''
    self.level = level

  def emit(self, level, *args, **kwargs):
    frame = kwargs.pop('frame', None)
    if level >= self.level:
      message = print_as_str(*args, **kwargs)
      emit(self.prefix, message, level, None, frame)

  def debug(self, *args, **kwargs):
    self.emit(DEBUG, *args, **kwargs)

  def info(self, *args, **kwargs):
    self.emit(INFO, *args, **kwargs)

  def warn(self, *args, **kwargs):
    self.emit(WARNING, *args, **kwargs)

  def error(self, *args, **kwargs):
    self.emit(ERROR, *args, **kwargs)

  def critical(self, *args, **kwargs):
    self.emit(CRITICAL, *args, **kwargs)

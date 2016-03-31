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

import os
import sys

try:
  import colorama
except ImportError:
  colorama = None

try:
  import termcolor
except ImportError:
  termcolor = None

# Only enable colorized output if attached to a TTY or if explicitly
# requested by the environment.
isatty = (sys.stdout.isatty() and sys.stderr.isatty())
if os.environ.get('CRAFTR_ISATTY') == 'true':
  isatty = True
elif os.environ.get('CRAFTR_ISATTY') == 'false':
  isatty = False

if isatty and colorama:
  colorama.init()


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
  print('\r\33[K', end='')


def colored(text, color=None, on_color=None, attrs=None):
  ''' Synonym for `termcolor.colored()` that can also be used if the
  module is not available, in which case *text* is returned unchanged. '''

  if not termcolor or not isatty:
    return text
  if isinstance(attrs, str):
    attrs = [attrs]
  elif not attrs:
    attrs = []
  return termcolor.colored(text, color, on_color, attrs)


def compile(color=None, on_color=None, attrs=None):
  ''' Compile an ANSI escape sequence and return it. Return an empty
  string if the `termcolor` module is not available. To reset the styling,
  use the `reset` string. '''

  if not termcolor or not isatty:
    return ''

  if isinstance(attrs, str):
    attrs = [attrs]
  elif not attrs:
    attrs = []

  res = ''
  fmt_str = '\033[%dm'
  for attr in attrs:
    res += fmt_str % termcolor.ATTRIBUTES[attr]
  if on_color is not None:
    res += fmt_str % termcolor.HIGHLIGHTS[on_color]
  if color is not None:
    res += fmt_str % termcolor.COLORS[color]

  return res


# ANSI code to reset the text styling.
reset = termcolor.RESET if (termcolor and isatty) else ''

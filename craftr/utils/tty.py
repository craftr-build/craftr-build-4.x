# The Craftr build system
# Copyright (C) 2016  Niklas Rosenstein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
:mod:`craftr.utils.tty`
=======================

This module provides colorized terminal output and other terminal helpers.
In order to colorize output, the :mod:`termcolor` module is required. On
Windows, the `colorama` module is also necessary.
"""

import os
import sys

# Attempt to import colorama and termcolor, but they are only required for
# colorization.
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
  """
  Determines the size of the terminal.
  """

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
  """
  Clears out the current line in the terminal completely and resets the
  curser to the first column.
  """

  print('\r\33[K', end='')


def colored(text, color=None, on_color=None, attrs=None):
  """
  Synonym for :func:`termcolor.colored()` that can also be used if the
  module is not available, in which case *text* is returned unchanged.
  """

  if not termcolor or not isatty:
    return text
  if isinstance(attrs, str):
    attrs = [attrs]
  elif not attrs:
    attrs = []
  return termcolor.colored(text, color, on_color, attrs)


def compile(color=None, on_color=None, attrs=None):
  """
  Compile an ANSI escape sequence and return it. Return an empty string if
  the :mod:`termcolor` module is not available. To reset the styling, use the
  :data:`reset` string.
  """

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


#: ANSI code to reset the text styling. Only available if the :mod:`termcolor`
#: module is available, otherwise it will be an empty string.
reset = termcolor.RESET if (termcolor and isatty) else ''

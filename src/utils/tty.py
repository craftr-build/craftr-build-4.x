"""
This module provides colorized terminal output and other terminal helpers.
In order to colorize output, the :mod:`termcolor` module is required. On
Windows, the `colorama` module is also necessary.
"""

import errno
import os
import re
import sys

# Import colorama and termcolor if available.
try: import colorama
except ImportError: colorama = None
try: import termcolor
except ImportError: termcolor = None

if os.environ.get('CRAFTR_ISATTY') == 'true':
  _enable_color = True
elif os.environ.get('CRAFTR_ISATTY') == 'false':
  _enable_color = False
else:
  _enable_color = (sys.stdout.isatty() and sys.stderr.isatty())
_colorama_initalized = False


def set_colorize_enabled(enabled):
  """
  Enable/disable colorization explicitly. The default state is derived from
  the environment when the #craftr.utils.term module is imported.
  """

  global _enable_color, _colorama_initalized, reset
  _enable_color = bool(enabled)
  if _enable_color and not _colorama_initalized and colorama:
    colorama.init()
    _colorama_initalized = True
  reset = termcolor.RESET if (termcolor and _enable_color) else ''


def terminal_size(default=(120, 30)):
  """
  Determines the size of the terminal. If the size can not be obtained, returns
  the specified *default* size.
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
      return (sizex, sizey)
    else:
      return default
  else:
    # http://stackoverflow.com/a/3010495/791713
    import fcntl, termios, struct
    try:
      data = fcntl.ioctl(0, termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0))
    except OSError as exc:
      # craftr-build/craftr#169 -- On OSX on Travis CI the call fails, probably
      # because the process is not attached to a TTY.
      if exc.errno in (errno.ENODEV, errno.ENOTTY):
        return default
      raise
    h, w, hp, wp = struct.unpack('HHHH', data)
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

  if not termcolor or not _enable_color:
    return text
  if isinstance(attrs, str):
    attrs = [attrs]
  elif not attrs:
    attrs = []
  if on_color:
    on_color = 'on_' + on_color
  return termcolor.colored(text, color, on_color, attrs)


def compile(color=None, on_color=None, attrs=None):
  """
  Compile an ANSI escape sequence and return it. Return an empty string if
  the :mod:`termcolor` module is not available. To reset the styling, use the
  :data:`reset` string.
  """

  if not termcolor or not _enable_color:
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
    res += fmt_str % termcolor.HIGHLIGHTS['on_' + on_color]
  if color is not None:
    res += fmt_str % termcolor.COLORS[color]

  return res


def format(value, *args, **kwargs):
  """
  Given a format string of the syntax `text %[attr,attr,...][text] text`,
  expands the format specifiers with the respective terminal color
  codes respectively. If *args* or *kwargs* are specified, the #str.format()
  function will be called on *value* beforehand.
  The first attribute must always be a color name. The second attribute may
  also be a color name but MUST be an `on_` color. You can also specify just
  and `on_` color. If you want to use a non-color attribute only, you need to
  prefix an empty attribute like `%[,blink][text here]`.
  # Example
  ```python
  >>> print(term.format('Hello %[red,on_white][{}]', name))
  Hello John
  """

  if args or kwargs:
    value = value.format(*args, **kwargs)

  def repl(match):
    attrs = match.group(1).split(',')
    if not attrs:
      raise ValueError('invalid term format specified, empty attributes list')
    color, on_color = attrs.pop(0), None
    if not color:
      color = None
    elif color.startswith('on_'):
      color, on_color = None, color[3:]
    if not on_color and attrs and attrs[0].startswith('on_'):
      on_color = attrs.pop(0)[3:]

    value = match.group(2).replace('\\]', ']')
    return colored(value, color, on_color, attrs)

  return re.sub(r'%\[([^\[\]]+)\]\[(.*?)(?<!\\)\]', repl, value)


#: ANSI color code to reset the terminal style. Initialized in
#: #set_colorize_enabled().
reset = ''


set_colorize_enabled(_enable_color)

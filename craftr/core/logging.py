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

from craftr.utils import tty

import abc
import contextlib
import itertools
import sys
import time
import werkzeug

DEBUG = 5
INFO = 10
WARNING = 15
ERROR = 20

class BaseLogger(object, metaclass=abc.ABCMeta):

  DEBUG = DEBUG
  INFO = INFO
  WARNING = WARNING
  ERROR = ERROR

  def debug(self, *args, **kwargs):
    self.log(DEBUG, *args, **kwargs)

  def info(self, *args, **kwargs):
    self.log(INFO, *args, **kwargs)

  def warn(self, *args, **kwargs):
    self.log(WARNING, *args, **kwargs)

  def error(self, *args, **kwargs):
    self.log(ERROR, *args, **kwargs)

  @contextlib.contextmanager
  def indent(self):
    self.add_indent(1)
    try:
      yield
    finally:
      self.add_indent(-1)

  @abc.abstractmethod
  def log(self, level, *object, sep=' ', end='\n', indent=0):
    pass

  @abc.abstractmethod
  def add_indent(self, level):
    pass

  @abc.abstractmethod
  def progress_begin(self, description, spinning):
    pass

  @abc.abstractmethod
  def progress_update(self, progress, info_text=''):
    pass

  @abc.abstractmethod
  def progress_end(self):
    pass

  @abc.abstractmethod
  def set_level(self, level):
    pass

  @abc.abstractmethod
  def flush(self):
    pass


class DefaultLogger(BaseLogger):

  level_colors = {
    DEBUG: 'yellow',
    INFO: 'white',
    WARNING: 'magenta',
    ERROR: 'red'
  }

  def __init__(self, stream=None, level=INFO, indent_seq='  '):
    self._stream = stream or sys.stdout
    self._level = level
    self._indent_seq = indent_seq
    self._indent = 0
    self._progress = None
    self._line_alive = False
    self._last_module_name = None

  def log(self, level, *objects, sep=' ', end='\n', indent=0):
    from craftr.core.session import session
    module = session.module if session else None
    if level < self._level:
      return
    width = tty.terminal_size()[0] - 1
    if self._progress:
      tty.clear_line()
    lines = sep.join(map(str, objects)).split('\n')
    prefix = '' if self._line_alive else self._indent_seq * (self._indent + indent)
    prefix += tty.compile(self.level_colors[level])

    if module:
      name = '(' + module.manifest.name + ':{})'.format(module.current_line)
    if lines and module and name != self._last_module_name:
      self._last_module_name = name
      rem = width - len(name)
      if len(lines[0]) < rem - 1:
        print(prefix + lines[0] + ' ' * (rem - 1 - len(lines[0])), name + tty.reset)
        lines.pop(0)
      else:
        print(' ' * rem + name)

    for line in lines:
      print(prefix + line + tty.reset, end=end, file=self._stream)
    self._line_alive = ('\n' not in end)
    if self._progress and 'progress' in self._progress:
      self.progress_update(self._progress['progress'], self._progress['info_text'], _force=True)
    self._stream.flush()

  def add_indent(self, levels):
    self._indent += levels

  def progress_begin(self, description=None, spinning=False):
    self._progress = {'description': description, 'spinning': spinning,
      'index': 0, 'last': 0}
    if description:
      self.info(description)

  def progress_update(self, progress, info_text='', *, _force=False):
    if not self._progress:
      return
    info_text = str(info_text)
    self._progress['progress'] = progress
    self._progress['info_text'] = info_text
    ctime = time.time()
    if not _force and ctime - self._progress['last'] < 0.25:
      return
    tty.clear_line()
    width = 30
    if self._progress['spinning']:
      sign = ('~--', '-~-', '--~')[self._progress['index'] % 3]
      bar = ''.join(itertools.islice(itertools.cycle(sign), width))
    else:
      intprogress = int(min([1.0, max([0.0, float(progress)])]) * width)
      bar = '#' * intprogress + ' ' * (width - intprogress)
    indent = self._indent_seq * self._indent
    print('{}|{}| {}'.format(indent, bar, info_text), end='', file=self._stream)
    self._progress['index'] += 1
    self._progress['last'] = ctime
    self._stream.flush()

  def progress_end(self):
    tty.clear_line()
    self._progress = None

  def set_level(self, level):
    self._level = level

  def flush(self):
    self._stream.flush()


_logger = DefaultLogger()
logger = werkzeug.LocalProxy(lambda: _logger)


def set_logger(logger):
  global _logger
  _logger = logger

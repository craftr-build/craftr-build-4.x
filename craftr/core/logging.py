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
import itertools
import sys
import time
import werkzeug


class BaseLogger(object, metaclass=abc.ABCMeta):

  def debug(self, *args, **kwargs):
    self.log('debug', *args, **kwargs)

  def info(self, *args, **kwargs):
    self.log('info', *args, **kwargs)

  def warn(self, *args, **kwargs):
    self.log('warn', *args, **kwargs)

  def error(self, *args, **kwargs):
    self.log('error', *args, **kwargs)

  @abc.abstractmethod
  def log(self, level, *object, sep=' ', end='\n', indent=0):
    pass

  @abc.abstractmethod
  def indent(self):
    pass

  @abc.abstractmethod
  def dedent(self):
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


class DefaultLogger(BaseLogger):

  level_colors = {
    'debug': 'yellow',
    'info': 'white',
    'warn': 'magenta',
    'error': 'red'
  }

  def __init__(self, stream=None, indent_seq='  '):
    self._stream = stream or sys.stdout
    self._indent_seq = indent_seq
    self._indent = 0
    self._progress = None
    self._line_alive = False

  def log(self, level, *objects, sep=' ', end='\n', indent=0):
    if self._progress:
      tty.clear_line()
    prefix = '' if self._line_alive else self._indent_seq * (self._indent + indent)
    prefix += tty.compile(self.level_colors[level])
    print(prefix + sep.join(map(str, objects)) + tty.reset, end=end, file=self._stream)
    self._line_alive = ('\n' not in end)
    if self._progress and 'progress' in self._progress:
      self.progress_update(self._progress['progress'], self._progress['info_text'], _force=True)

  def indent(self):
    self._indent += 1

  def dedent(self):
    self._indent -= 1
    if self._indent < 0:
      self._indent = 0

  def progress_begin(self, description, spinning=False):
    self._progress = {'description': description, 'spinning': spinning,
      'index': 0, 'last': 0}
    self.info(description)

  def progress_update(self, progress, info_text='', *, _force=False):
    self._progress['progress'] = progress
    self._progress['info_text'] = info_text
    ctime = time.time()
    if not _force and ctime - self._progress['last'] < 0.25:
      return
    tty.clear_line()
    width = tty.terminal_size()[0] - len(info_text) - 5  # safe margin
    if self._progress['spinning']:
      sign = ('~--', '-~-', '--~')[self._progress['index'] % 3]
      bar = ''.join(itertools.islice(itertools.cycle(sign), width))
    else:
      intprogress = int(min([1.0, max([0.0, float(progress)])]) * width)
      bar = '=' * intprogress + ' ' * (width - intprogress)
    print('[{}] {}'.format(bar, info_text), end='', file=self._stream)
    self._progress['index'] += 1
    self._progress['last'] = ctime

  def progress_end(self):
    tty.clear_line()
    self._progress = None


_logger = DefaultLogger()
logger = werkzeug.LocalProxy(lambda: _logger)


def set_logger(logger):
  global _logger
  _logger = logger

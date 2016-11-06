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

import abc
import itertools
import sys


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
  def log(self, level, *object, sep=' ', end='\n'):
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

  def __init__(self, stream=None, indent_seq='  '):
    self._stream = stream or sys.stdout
    self._indent_seq = indent_seq
    self._indent = 0
    self._progress = None
    self._line_alive = False

  def log(self, level, *objects, sep=' ', end='\n'):
    # TODO: Clear the current line completely if we're currently in a progress.
    prefix = '' if self._line_alive else self._indent_seq * self._indent
    print(prefix + sep.join(map(str, objects)), end=end, file=self._stream)
    self._line_alive = ('\n' not in end)

  def indent(self):
    self._indent += 1

  def dedent(self):
    self._indent -= 1
    if self._indent < 0:
      self._indent = 0

  def progress_begin(self, description, spinning=False):
    self._progress = {'description': description, 'spinning': spinning}
    self.info(description)

  def progress_update(self, progress, info_text=''):
    # TODO: Clear current line completely and get terminal width
    width = 60
    if self._progress['spinning']:
      print('\r[' + '~' * width + ']', info_text, end='', file=self._stream)
    else:
      progress = int(min([1.0, max([0.0, float(progress)])]) * width)
      print('\r[' + '=' * progress + ' ' * (width - progress) + ']', info_text, end='', file=self._stream)

  def progress_end(self):
    print('\r', end='', file=self._stream)
    self._progress = None

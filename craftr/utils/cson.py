# The Craftr build system
# Copyright (C) 2017  Niklas Rosenstein
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
A wrapper around the #!cson module which wraps all exceptions in a common
#Error exception type and gives proper error messages.
"""

import cson as _cson


class Error(Exception):

  def __init__(self, message, exc=None):
    self.message = message
    self.exc = exc

  def __str__(self):
    return str(self.message)


def load(*args, **kwargs):
  """
  Wrapper for #!cson.load(). Accepts an additional *filename* parameter that
  will be included in the error message.
  """

  filename = kwargs.pop('filename', None)
  try:
    return _cson.load(*args, **kwargs)
  except _cson.ParseError as exc:
    msg = 'parse error: {}'.format(exc)
    if filename:
      msg = '{}: {}'.format(filename, msg)
    raise Error(msg, exc)


def dump(*args, **kwargs):
  filename = kwargs.pop('filename', None)
  try:
    return _cson.dump(*args, **kwargs)
  except TypeError as exc:
    msg = str(exc)
    if filename:
      msg = '{}: {}'.format(filename, msg)
    raise Error(msg, exc)

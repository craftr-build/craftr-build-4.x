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

import contextlib
import sys


def flatten(iterable):
  """
  Flattens two levels of nested iterables into a single list.
  """

  return [item for subiterable in iterable for item in subiterable]


def import_(fqn):
  """
  Given a fully qualified name, imports the object and returns it.

  :param fqn: The full name of the object to import, including the module
    name to import it from.
  :raise ImportError: If the object can not be imported.
  :return: any
  """

  parts = iter(fqn.split('.'))
  snake = ''

  # Import module and submodules until we can no longer import modules.
  result = None
  imp_error = None
  for part in parts:
    try:
      # fromlist argument non-empty to get bottom-most module returned.
      result = __import__(snake + part, fromlist=['foo'], level=0)
    except ImportError as exc:
      imp_error = exc
      break
    snake += part + '.'
    part = None

  if result is None and imp_error:
    raise imp_error
  elif result is None:
    raise ImportError(snake.rstrip('.'))

  try:
    if part:
      result = getattr(result, part)
    for part in parts:
      result = getattr(result, part)
  except AttributeError:
    raise ImportError(fqn)

  return result


def unique_append(lst, item):
  if item not in lst:
    lst.append(item)


def unique_extend(lst, iterable):
  for item in iterable:
    if item not in lst:
      lst.append(item)


def unique_list(iterable):
  result = []
  for item in iterable:
    if item not in result:
      result.append(item)
  return result


def strip_flags(command, flags):
  """
  Remove all occurences of all *flags* in the *command* list. The list is
  mutated directlry.

  :param command: A list of command-line arguments.
  :param remove_flags: An iterable of flags to remove.
  :return: The *command* parameter.
  """

  # Remove the specified flags and keep every flag that could not
  # be removed from the command.
  flags = set(flags)
  for flag in list(flags):
    count = 0
    while True:
      try:
        command.remove(flag)
      except ValueError:
        break
      count += 1
    if count != 0:
      flags.remove(flag)
  if flags:
    fmt = ' '.join(shell.quote(x) for x in flags)
    logger.warn("flags not removed: " + fmt)

  return command


@contextlib.contextmanager
def combine_context(*inputs):
  """
  Combines multiple context managers.
  """

  try:
    for ctx in inputs:
      ctx.__enter__()
    yield inputs
  finally:
    raise_later = []
    for ctx in inputs:
      try:
        ctx.__exit__(*sys.exc_info())
      except BaseException:
        raise_later.append(sys.exc_info())
    for exc_type, exc_value, exc_tb in raise_later:
      raise exc_value.with_traceback(exc_tb)

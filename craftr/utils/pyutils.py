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

  if result is None and imp_error:
    raise imp_error
  elif result is None:
    raise ImportError(snake.rstrip('.'))

  try:
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

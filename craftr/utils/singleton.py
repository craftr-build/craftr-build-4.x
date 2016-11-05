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

def make_singleton(name, type_name=None, as_bool=True):
  """
  Create a single type and return its only instance with the
  specified #name. If #type_name is not specified, it is automatically
  derived from the singleton #name.
  """

  class singleton_class(object):
    __instance = None
    def __new__(cls):
      if cls.__instance is None:
        cls.__instance = super().__new__(cls)
      return cls.__instance
    def __str__(self):
      return name
    def __repr__(self):
      return name
    def __bool__(self):
      return as_bool
    __nonzero__ = __bool__

  if type_name is None:
    type_name = name + 'Type'
  singleton_class.__name__ = type_name
  return singleton_class()

#: A singleton object like :const:`None`, :const:`True` or :const:`False`.
#: Can be used to denote the default value of an argument when :const:`None`
#: is an accepted non-default value.
Default = make_singleton('Default')

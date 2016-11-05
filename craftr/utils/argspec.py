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

import collections

def tn(value):
  return type(value).__name__

def validate(name, value, schema):
  """
  A helper function to validate function parameters type and value.
  The *schema* must be a dictionary and supports the following keys:

  - ``type``: A single type or a list of accepted types
  - ``bool_validators``: A function or a list of functions that return
    True if the *value* is valid, False otherwise.
  - ``validators``: A function or a list of functions that raise a
    :class:`ValueError` if the *value* is invalid.
  - ``items``: If *value* is a sequence, this key must provide a sub-schema
    that holds true for all of the items in the sequence. Note that it will
    not be applied to iterables.
  - ``allowEmpty``: If specified, must be True or False. If True, allows
    *value* to be an empty sequence, otherwise not.
  """

  schema.setdefault('type', [])
  schema.setdefault('bool_validators', [])
  schema.setdefault('validators', [])

  if isinstance(schema['type'], list):
    schema['type'] = tuple(schema['type'])
  elif not isinstance(schema['type'], tuple):
    schema['type'] = (schema['type'],)
  schema['type'] = tuple(type(None) if x is None else x for x in schema['type'])

  if schema['type'] and not isinstance(value, schema['type']):
    raise TypeError("argument '{}' expected one of {} but got {}".format(
      name, '{'+','.join(x.__name__ for x in schema['type'])+'}', tn(value)))
  if isinstance(value, collections.Sequence):
    if 'items' in schema:
      for index, item in enumerate(value):
        validate('{}[{}]'.format(name, index), item, schema['items'])
    if not schema.get('allowEmpty', True) and not value:
      raise ValueError("argument '{}' can not be empty".format(name))

  if not isinstance(schema['bool_validators'], (list, tuple)):
    schema['bool_validators'] = [schema['bool_validators']]
  for validator in schema['bool_validators']:
    if not validator(value):
      raise TypeError("argument '{}' is not {}".format(name, validator.__name__))

  if not isinstance(schema['validators'], (list, tuple)):
    schema['validators'] = [schema['validators']]
  for validator in schema['validators']:
    validator(value)

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
:mod:`craftr.core.manifest`
===========================

This module implemenets parsing and representing the manifest files of
Craftr packages. Every Craftr package also provides a Craftr module which
can be loaded with the ``require()`` function.

Example manifest:

.. code:: json

  {
    "name": "username.packagename",
    "version": "1.0.3",
    "main": "Craftrfile",  // default
    "author": "User Name <username@nameuser.org>",
    "url": "https://github.com/username/packagename",
    "dependencies": {
      "another_user.another_package": "1.x"
    },
    "options": {
      "BOOSTDIR": {
        "type": "string"
      }
    }
  }
"""

from nr.types.recordclass import recordclass
from nr.types.version import Version, VersionCriteria

import json
import jsonschema
import re


def validate_package_name(name):
  """
  Validates the package *name*. A valid package name must consist only
  of letters, digits, hyphes, underscores and periods. The first character
  of a package must be a letter or digit.

  :raise ValueError: If *name* is not a valid package name.
  """

  if not isinstance(name, str):
    raise TypeError("package name must be str but got {!r}".format(tn(name)))
  if not re.match(r'^[A-z0-9][A-z0-9\.\-\_]*$', name):
    raise ValueError("invalid package name: {!r}".format(name))


class BaseOption(object):
  """
  Base class for option value processors that convert and validate options
  from string values (usually provided via the command-line or environment
  variables).

  .. attribute:: name

  .. attribute:: inherit

  .. attribute:: help
  """

  def __init__(self, name, inherit=True, help=None):
    self.name = name
    self.inherit = inherit
    self.help = None

  def __call__(self, string):
    raise NotImplementedError


class BoolOption(BaseOption):

  def __init__(self, name, default=False, **kwargs):
    super().__init__(name, **kwargs)
    self.default = default

  def __call__(self, value):
    if isinstance(value, str):
      value = value.strip().lower()
      if value in ('yes', 'true', '1'):
        return True
      elif value in ('no', 'false', '0'):
        return False
      elif value == '':
        return self.default
    raise ValueError("invalid value for bool option: {!r}".format(value))


class TripletOption(BoolOption):

  def __init__(self, name, default=None, **kwargs):
    super().__init__(name, default, **kwargs)

  def __call__(self, value):
    try:
      return super().__call__(value)
    except ValueError:
      if isinstance(value, str):
        value = value.strip().lower()
        if value in ('null', 'None'):
          return None
      elif value is None:
        return None
    raise ValueError("invalid value for triplet option: {0!r}".format(value))


class StringOption(BaseOption):

  def __init__(self, name, default='', **kwargs):
    super().__init__(name, **kwargs)
    self.default = default

  def __call__(self, string):
    return string


class Namespace(object):
  """
  An empty class which is used to assign arbitrary attributes to. An instance
  of this class is created by :meth:`Manifest.get_options_namespace`.
  """

  def __str__(self):
    attrs = ', '.join('{}={!r}'.format(k, v) for k, v in vars(self).items())
    return 'Namespace({})'.format(attrs)


class InvalidManifest(Exception):
  """
  This exception can be raised by :meth:`Manifest.parse`
  """


class Manifest(recordclass):
  """
  Represents the manifest of a Craftr package. The manifest contains the basic
  information about the package name, version and its dependencies, as well as
  its author and homepage URL.

  .. attribute:: name

    The name of the Craftr package.

  .. attribute:: version

    The version of the Craftr package. This must be a semantic version
    number parsable by the :class:`Version` class.

  .. attribute:: main

    The name of the main build script that is executed for the package.
    If this member is None, Craftr will interpret it as the default value
    specified in the :class:`craftr.core.session.Session`.

  .. attribute:: author

    Name of the package author.

  .. attribute:: url

    The homepage of the project of this package.

  .. attribute:: dependencies

    A dictionary that maps package names to version critiera parsable by
    the :class:`VersionCriteria` class. The criteria is very similar to
    Node.js version selectors.

  .. attribute:: options

    A dictionary of options that can be provided by the user before
    Craftr is being executed. Currently, there are only boolean and
    string values supported. The JSON format is one of the following

    .. code:: json

      "options": {
        "my_option_name": "bool",
        "my_other_option": "string"
      }
      // or
      "options": {
        "my_option_name": {
          "type": "bool",
          "default": false
        },
        "my_other_option": {
          "type": "string",
          "default": ""
        }
      }
  """

  Schema = {
    "type": "object",
    "required": ["name", "version"],
    "properties": {
      "name": {"type": "string"},
      "version": {"type": "string"},
      "main": {"type": "string"},
      "author": {"type": "string"},
      "url": {"type": "string"},
      "dependencies": {
        "type": "object",
        "additionalProperties": {"type": "string"}
      },
      "options": {
        "type": "object",
        "additionalProperties": {
          "oneOf": [
            {
              "type": "string",
              "enum": ["bool", "triplet", "string"]
            },
            {
              "type": "object",
              "properties": {
                "type": {"type": "string", "enum": ["bool"]},
                "default": {"type": "boolean"},
                "inherit": {"type": "boolean"},
                "help": {"type": "string"}
              }
            },
            {
              "type": "object",
              "properties": {
                "type": {"type": "string", "enum": ["triplet"]},
                "default": {"type": ["null", "boolean"]},
                "inherit": {"type": "boolean"},
                "help": {"type": "string"}
              }
            },
            {
              "type": "object",
              "properties": {
                "type": {"type": "string", "enum": ["string"]},
                "default": {"type": "string"},
                "inherit": {"type": "boolean"},
                "help": {"type": "string"}
              }
            }
          ]
        }
      }
    }
  }

  Invalid = InvalidManifest
  OptionTypeMapping = {"bool": BoolOption, "triplet": TripletOption,
                       "string": StringOption}

  __slots__ = tuple(Schema['properties'].keys())

  def __init__(self, name, version, main=None, author=None, url=None,
               dependencies=None, options=None):
    if version is not None:
      version = Version(version)
    self.name = name
    self.version = version
    self.main = main
    self.author = author
    self.url = url
    self.dependencies = dependencies or {}
    self.options = options or {}

  def get_options_namespace(self, provider):
    """
    Create a :class:`Namespace` object filled with the option values specified
    in the manifest where the option values are read from *provider*.

    @param provider: A dictionary that provides option values.
    @return Namespace
    """

    ns = Namespace()
    for key, option in self.options.items():
      value = provider.get(self.name + '.' + option.name, NotImplemented)
      if value is NotImplemented and option.inherit:
        value = provider.get(option.name)
      if value is NotImplemented or value is None:
        value = option.default
      else:
        try:
          value = option(value)
        except ValueError as exc:
          raise ValueError('{}.{}: {}'.format(self.name, option.name, exc))
      setattr(ns, key, value)
    return ns

  @staticmethod
  def parse(file):
    """
    Parses a manifest file and returns a new :class:`Manifest` object.

    :param file: A filename or file-like object in JSON format.
    :raise InvalidManifest: If the file is not a valid JSON file or the
      manifest data is invalid or inconsistent.
    :return: A :class:`Manifest` object.
    """

    try:
      if isinstance(file, str):
        with open(file) as fp:
          data = json.load(fp)
      else:
        data = json.load(file)
      jsonschema.validate(data, Manifest.Schema)
    except (json.JSONDecodeError, jsonschema.ValidationError) as exc:
      raise Manifest.Invalid(exc)

    try:
      validate_package_name(data['name'])
    except ValueError:
      raise Manifest.Invalid("invalid package name: {!r}".format(data['name']))

    data.setdefault('dependencies', {})
    for key, value in data['dependencies'].items():
      try:
        data['dependencies'][key] = VersionCriteria(value)
      except ValueError as exc:
        msg = 'invalid version critiera for {0!r}: {1!r}'
        raise Manifest.Invalid(msg.format(key, value))

    data.setdefault('options', {})
    for key, value in data['options'].items():
      if isinstance(value, str):
        value = {"type": value}
      option_type = Manifest.OptionTypeMapping[value.pop('type')]
      try:
        data['options'][key] = option_type(key, **value)
      except TypeError as exc:
        raise Manifest.Invalid(exc)

    try:
      return Manifest(**data)
    except TypeError as exc:
      raise Manifest.Invalid(exc)

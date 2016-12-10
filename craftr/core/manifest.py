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
    "main": "Craftrfile",
    "author": "User Name <username@nameuser.org>",
    "url": "https://github.com/username/packagename",
    "dependencies": {
      "another_user.another_package": "1.x"
    },
    "options": {
      "directory": "path",
      "version": "string"
    }
  }
"""

from craftr.core.logging import logger
from craftr.utils import httputils
from craftr.utils import path
from craftr.utils import pyutils
from nr.types.recordclass import recordclass
from nr.types.version import Version, VersionCriteria

import abc
import fnmatch
import io
import json
import jsonschema
import nr.misc.archive
import re
import string
import urllib.request


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

  .. attribute:: project_dir

    Relative path to the project directory. Local paths in the build script
    are automatically assumed relative to this directory. Defaults to ``..``.

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
    Craftr is being executed. The option name maps to a :class:`BaseOption`
    instance.
  """

  Schema = {
    "type": "object",
    "required": ["name", "version"],
    "properties": {
      "name": {"type": "string"},
      "version": {"type": "string"},
      "description": {"type": "string"},
      "main": {"type": "string"},
      "project_dir": {"type": "string"},
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
            # Plain type description
            {
              "type": "string"
            },
            # Detailed option description
            {
              "type": "object",
              "properties": {
                "type": {"type": "string"}
              },
              "additionalProperties": True
            }
          ]
        }
      }
    }
  }

  Invalid = InvalidManifest

  __slots__ = tuple(Schema['properties'].keys())

  def __init__(self, name, version, main='Craftrfile', project_dir='.',
               description=None, author=None, url=None, dependencies=None,
               options=None):
    if version is not None:
      version = Version(version)
    self.name = name
    self.version = version
    self.main = main
    self.project_dir = project_dir
    self.description = description
    self.author = author
    self.url = url
    self.dependencies = dependencies or {}
    self.options = options or {}

  def get_options_namespace(self, provider, errors=None):
    """
    Create a :class:`Namespace` object filled with the option values specified
    in the manifest where the option values are read from *provider*.

    :param provider: A dictionary that provides option values.
    :param errors: A list to which tuples of error information will be
      appended. The tuples are in the format (option, value, exc).
    :return Namespace
    """

    if errors is None:
      errors = []
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
          errors.append((option, value, exc))
          value = option.default
      setattr(ns, key, value)
    return ns

  @staticmethod
  def parse_string(string):
    """
    Shortcut for wrapping *string* in a file-like object and padding it to
    :func:`parse`.
    """

    return Manifest.parse(io.StringIO(string))

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
      type_name = value.pop('type')
      if '.' not in type_name:
        type_name = __name__ + '._aliases.' + type_name
      try:
        option_type = pyutils.import_(type_name)
      except ImportError:
        option_type = None
      if not isinstance(option_type, type) or not issubclass(option_type, BaseOption):
        raise Manifest.Invalid('invalid option type: {!r}'.format(type_name))
      try:
        data['options'][key] = option_type(key, **value)
      except TypeError as exc:
        raise Manifest.Invalid(exc)

    try:
      return Manifest(**data)
    except TypeError as exc:
      raise Manifest.Invalid(exc)


class BaseOption(object, metaclass=abc.ABCMeta):
  """
  Base class for option value processors that convert and validate options
  from string values (usually provided via the command-line or environment
  variables).

  .. attribute:: name

  .. attribute:: inherit

  .. attribute:: help

  .. attribute:: default
  """

  def __init__(self, name, inherit=True, help=None, default=None):
    self.name = name
    self.inherit = inherit
    self.help = None
    self.default = default

  @abc.abstractmethod
  def __call__(self, value):
    """
    Convert the string *value* to the respective Python representation.
    """


class BoolOption(BaseOption):
  """
  Represents a boolean option. Supports the identifiers "yes", "true",
  "1", "no", "false" and "0".
  """

  def __init__(self, name, default=False, **kwargs):
    super().__init__(name, default=default, **kwargs)

  def __call__(self, value):
    if isinstance(value, str):
      value = value.strip().lower()
      if value in ('yes', 'true', '1'):
        return True
      elif value in ('no', 'false', '0'):
        return False
      elif value == '':
        return self.default
      else:
        raise ValueError("invalid value for bool option: {!r}".format(value))
    else:
      return bool(value)


class TripletOption(BoolOption):
  """
  Just like the :class:`BoolOption` but with a third option, accepting
  "null" and "none" (which maps to :const:`None`).
  """

  def __call__(self, value):
    try:
      return super().__call__(value)
    except ValueError:
      if isinstance(value, str):
        value = value.strip().lower()
        if value in ('null', 'none'):
          return None
      elif value is None:
        return None
    raise ValueError("invalid value for triplet option: {0!r}".format(value))


class StringOption(BaseOption):
  """
  Plain-string option.
  """

  def __init__(self, name, default='', **kwargs):
    super().__init__(name, **kwargs)
    self.default = default

  def __call__(self, string):
    return string


class PathOption(StringOption):
  """
  Option for paths. Relative paths are automatically converted to absolute
  paths. It is assumed that relative paths are specified relative to
  :attr:`Session.maindir`.
  """

  def __call__(self, value):
    from craftr.core.session import session
    if not path.isabs(value):
      value = path.join(session.maindir, value)
    return path.norm(value)


class _aliases:
  """
  This class serves as a namespace in order to be able to specify the
  standard option and loader types by their shortcut name in the manifest
  rather than by their FQN.
  """

  bool = BoolOption
  triplet = TripletOption
  string = StringOption
  path = PathOption

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

from craftr.core.logging import logger
from craftr.utils import path

import configparser
import re


def read_config_file(filename, basedir=None, follow_include_directives=True):
  """
  Reads a configuration file and returns a dictionary of the values that
  it contains. The format is standard :mod:`configparser` ``.ini`` style,
  however this function supports ``include`` directives that can include
  additional configuration files.

  ::

    [include "path/to/config.ini"]            ; errors if the file does not exist
    [include "path/to/config.ini" if-exists]  ; ignored if the file does not exist

  :param filename: The name of the configuration file to read.
  :param basedir: If *filename* is not an absolute path or the base directory
    should be altered, this is the directory of which to look for files
    specified with ``include`` directives.
  :param follow_include_directives: If this is True, ``include`` directives
    will be followed.
  :raise FileNotFoundError: If *filename* does not exist.
  :raise InvalidConfigError: If the configuration format is invalid. Also
    if any of the included files do not exist.
  :return: A dictionary. Section names are prepended to the option names.
  """

  filename = path.norm(filename)
  if not basedir:
    basedir = path.dirname(filename)

  logger.debug('reading configuration file:', filename)
  if not path.isfile(filename):
    raise FileNotFoundError(filename)
  parser = configparser.SafeConfigParser()
  try:
    parser.read([filename])
  except configparser.Error as exc:
    raise InvalidConfigError('"{}": {}'.format(filename, exc))

  result = {}
  for section in parser.sections():
    match = re.match('include\s+"([^"]+)"(\s+if-exists)?$', section)
    if match:
      if not follow_include_directives:
        continue
      ifile, if_exists = match.groups()
      ifile = path.norm(ifile, basedir)
      try:
        result.update(read_config_file(ifile))
      except FileNotFoundError as exc:
        if not if_exists:
          raise InvalidConfigError('file "{}" included by "{}" does not exist'
              .format(str(exc), filename))
    else:
      for option in parser.options(section):
        result['{}.{}'.format(section, option)] = parser.get(section, option)

  return result


class InvalidConfigError(Exception):
  pass

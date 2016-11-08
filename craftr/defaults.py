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
:mod:`craftr.defaults`
======================

This module provides the default global namespace for Craftr modules. Names
starting with an underscore will be ignored.
"""

from craftr.core.logging import logger
from craftr.core.session import session
from craftr.utils import path

import require
import sys as _sys

require = require.Require(write_bytecode=False)


def include_defs(filename, globals=None):
  """
  Uses :mod:`require` to load a Python file and then copies all symbols
  that do not start with an underscore into the *globals* dictionary. If
  *globals* is not specified, it will fall back to the globals of the frame
  that calls the function.
  """

  module = require(filename, _stackdepth=1)
  if globals is None:
    globals = _sys._getframe(1).f_globals
  for key, value in vars(module).items():
    if not key.startswith('_'):
      globals[key] = value


def glob(patterns, exclude=(), include_dotfiles=False, parent=None):
  """
  Wrapper for :func:`path.glob` that automatically uses the current modules
  project directory for the *parent* argument if it has not been specifically
  set.
  """

  if parent is None and session and session.module:
    parent = session.module.project_directory

  return path.glob(patterns, exclude, include_dotfiles, parent)

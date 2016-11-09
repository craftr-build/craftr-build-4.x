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
from craftr.core.session import session, ModuleNotFound
from craftr.utils import path
from craftr.targetbuilder import gtn, TargetBuilder, Framework

import builtins as _builtins
import itertools as _itertools
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


def glob(patterns, parent=None, exclude=(), include_dotfiles=False):
  """
  Wrapper for :func:`path.glob` that automatically uses the current modules
  project directory for the *parent* argument if it has not been specifically
  set.
  """

  if parent is None and session and session.module:
    parent = session.module.project_directory

  return path.glob(patterns, parent, exclude, include_dotfiles)


def local(rel_path):
  """
  Given a relative path, returns the absolute path relative to the current
  module's project directory.
  """

  parent = session.module.project_directory
  return path.norm(rel_path, parent)


def buildlocal(rel_path):
  """
  Given a relative path, returns the path (still relative) to the build
  directory for the current module. This is basically a shorthand for
  prepending the module name and version to *path*.
  """

  if path.isabs(rel_path):
    raise ValueError('rel_path must be a relative path')
  return path.canonical(path.join(session.module.ident, rel_path))


def relocate_files(files, outdir, suffix, replace_suffix=True):
  """
  Converts a list of filenames, relocating them to *outdir* and replacing
  their existing suffix. If *suffix* is a callable, it will be passed the
  new filename and expected to return the same filename, eventually with
  a different suffix.
  """

  outdir = buildlocal(outdir)
  base = path.common(files)
  result = []
  for filename in files:
    filename = path.join(outdir, path.rel(filename, base))
    filename = path.addsuffix(filename, suffix, replace=replace_suffix)
    result.append(filename)
  return result


def filter(predicate, iterable):
  """
  Alternative for the built-in ``filter()`` function that returns a list
  instead of an iterable (which is the behaviour since Python 3).
  """

  result = []
  for item in iterable:
    if predicate(item):
      result.append(item)
  return result


def map(procedure, iterable):
  """
  Alternative for the built-in ``map()`` function that returns a list instead
  of an iterable (which is the behaviour since Python 3).
  """

  result = []
  for item in iterable:
    result.append(procedure(item))
  return result


def zip(*iterables, fill=NotImplemented):
  """
  Alternative to the Python built-in ``zip()`` function. This function returns
  a list rather than an iterable and also supports swapping to the
  :func:`itertools.izip_longest` version if the *fill* parameter is specified.
  """

  if fill is NotImplemented:
    return list(_builtins.zip(*iterables))
  else:
    return list(_itertools.zip_longest(*iterables, fillvalue=fill))


def load_module(name, into=None, get_namespace=True):
  """
  Load a Craftr module by name and return it. If *into* is specified, it must
  be a dictionary that will be filled with all the members of the module. Note
  that this function returns the namespace object of the module rather than
  the actual :class:`craftr.core.session.Module` object that wraps the module
  information unless *get_namespace* is False.

  The version criteria is read from the current module's manifest.

  :param name: The name of the module to load.
  :param into: If specified, must be a dictionary.
  :param get_namespace:
  :return: The module namespace object (of type :class:`types.ModuleType`)
    or the actual :class:`craftr.core.session.Module` if *get_namespace*
    is False.
  :raise ModuleNotFound: If the module could not be found.
  :raise RuntimeError: If the module that is attempted to be loaded is not
    declared in the current module's manifest.
  """

  if not session:
    raise RuntimeError('no session context')
  module = session.module
  if not module:
    raise RuntimeError('no current module')

  if name not in module.manifest.dependencies:
    raise RuntimeError('"{}" can not load "{}", make sure that it is listed '
        'in the dependencies'.format(module.ident, name))

  loaded_module = session.find_module(name, module.manifest.dependencies[name])
  loaded_module.run()

  if into is not None:
    for key, value in vars(loaded_module.namespace).items():
      if not key.startswith('_'):
        into[key] = value

  if get_namespace:
    return loaded_module.namespace
  return loaded_module

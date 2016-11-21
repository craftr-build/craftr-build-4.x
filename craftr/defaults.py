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

from craftr.core import build as _build
from craftr.core.logging import logger
from craftr.core.session import session, ModuleNotFound
from craftr.utils import path, shell
from craftr.targetbuilder import gtn, TargetBuilder, Framework
from craftr import platform

import builtins as _builtins
import itertools as _itertools
import require
import sys as _sys

require = require.Require(write_bytecode=False)


class ToolDetectionError(Exception):
  pass


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
    return rel_path
  return path.canonical(path.join(session.module.ident, rel_path))


def relocate_files(files, outdir, suffix, replace_suffix=True):
  """
  Converts a list of filenames, relocating them to *outdir* and replacing
  their existing suffix. If *suffix* is a callable, it will be passed the
  new filename and expected to return the same filename, eventually with
  a different suffix.
  """

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


def load_module(name, into=None, get_namespace=True, _stackframe=1):
  """
  Load a Craftr module by name and return it. If *into* is specified, it must
  be a dictionary that will be filled with all the members of the module. Note
  that this function returns the namespace object of the module rather than
  the actual :class:`craftr.core.session.Module` object that wraps the module
  information unless *get_namespace* is False.

  The version criteria is read from the current module's manifest.

  :param name: The name of the module to load. If this name is suffixed
    with the two characters ``.*`` and the *into* parameter is :const:`None`,
    the contents of the module will be exported into the globals of the
    calling frame.
  :param into: If specified, must be a dictionary.
  :param get_namespace:
  :return: The module namespace object (of type :class:`types.ModuleType`)
    or the actual :class:`craftr.core.session.Module` if *get_namespace*
    is False.
  :raise ModuleNotFound: If the module could not be found.
  :raise RuntimeError: If the module that is attempted to be loaded is not
    declared in the current module's manifest.

  Examples:

  .. code:: python

    cxx = load_module('lang.cxx')
    load_module('lang.cxx.*')
    assert cxx.c_compile is c_compile
  """

  if name.endswith('.*') and into is None:
    name = name[:-2]
    into = _sys._getframe(_stackframe).f_globals

  if not session:
    raise RuntimeError('no session context')
  module = session.module
  if not module:
    raise RuntimeError('no current module')

  if name not in module.manifest.dependencies:
    raise RuntimeError('"{}" can not load "{}", make sure that it is listed '
        'in the dependencies'.format(module.ident, name))

  loaded_module = session.find_module(name, module.manifest.dependencies[name])
  if not loaded_module.executed:
    loaded_module.run()

  if into is not None:
    module_builtins = frozenset('loader project_dir options'.split())
    all_vars = getattr(loaded_module.namespace, '__all__', None)
    for key, value in vars(loaded_module.namespace).items():
      if all_vars is not None:
        if key in all_vars:
          into[key] = value
      else:
        if not key.startswith('_') and key not in module_builtins and key not in globals():
          into[key] = value

  if get_namespace:
    return loaded_module.namespace
  return loaded_module


def gentool(command, preamble=None, environ=None, name=None):
  """
  Create a :class:`~_build.Tool` object. The name of the tool will be derived
  from the variable name it is assigned to unless *name* is specified.
  """

  tool = _build.Tool(gtn(name), command, preamble, environ)
  session.graph.add_tool(tool)
  return tool


def gentarget(command, inputs=(), outputs=(), *args, **kwargs):
  """
  Create a :class:`~_build.Target` object. The name of the target will be
  derived from the variable name it is assigned to unless *name* is specified.
  """

  target = _build.Target(gtn(kwargs.pop('name', None)), command, inputs,
      outputs, *args, **kwargs)
  session.graph.add_target(target)
  return target


def open_buildfile(name, mode='w'):
  """
  Creates a file with the specified *name* in a buildlocal directory named
  "buildfiles/". The returned object is file-like but must not necessarily
  represent the actual file on the filesystem. In case the current Session
  does not export build files, the returned object will simply be an in-memory
  file buffer that will be discarded.

  The ``fp.name`` attribute can be read to get the filename in either case.
  """

  # TODO: Check if the session exports or not.
  dirname = buildlocal('buildfiles')
  path.makedirs(dirname)
  return open(path.join(dirname, name), mode)


def error(*message):
  """
  Raises a :class:`ModuleError`.
  """

  raise ModuleError(' '.join(map(str, message)))


class ModuleError(Exception):
  pass

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
from craftr.core.manifest import Namespace
from craftr.core.session import session, ModuleNotFound
from craftr.utils import path, shell
from craftr.targetbuilder import gtn, TargetBuilder, Framework
from craftr import platform

import builtins as _builtins
import itertools as _itertools
import os as _os
import require
import sys as _sys

require = require.Require(write_bytecode=False)


class ToolDetectionError(Exception):
  pass


class ModuleError(Exception):
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
    parent = session.module.project_dir

  return path.glob(patterns, parent, exclude, include_dotfiles)


def local(rel_path):
  """
  Given a relative path, returns the absolute path relative to the current
  module's project directory.
  """

  parent = session.module.project_dir
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


def relocate_files(files, outdir, suffix, replace_suffix=True, parent=None):
  """
  Converts a list of filenames, relocating them to *outdir* and replacing
  their existing suffix. If *suffix* is a callable, it will be passed the
  new filename and expected to return the same filename, eventually with
  a different suffix.
  """

  if parent is None:
    parent = session.module.project_dir
  result = []
  for filename in files:
    filename = path.join(outdir, path.rel(filename, parent))
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


def load_file(filename):
  """
  Loads a Python file into a new module-like object and returns it. The
  *filename* is assumed relative to the currently executed module's
  directory (NOT the project directory which can be different).
  """

  if not path.isabs(filename):
    filename = path.join(session.module.directory, filename)

  with open(filename, 'r') as fp:
    code = compile(fp.read(), filename, 'exec')

  scope = Namespace()
  vars(scope).update(globals())
  exec(code, vars(scope))
  return scope


def gentool(commands, preamble=None, environ=None, name=None):
  """
  Create a :class:`~_build.Tool` object. The name of the tool will be derived
  from the variable name it is assigned to unless *name* is specified.
  """

  tool = _build.Tool(gtn(name), commands, preamble, environ)
  session.graph.add_tool(tool)
  return tool


def gentarget(commands, inputs=(), outputs=(), *args, **kwargs):
  """
  Create a :class:`~_build.Target` object. The name of the target will be
  derived from the variable name it is assigned to unless *name* is specified.
  """

  target = _build.Target(gtn(kwargs.pop('name', None)), commands, inputs,
      outputs, *args, **kwargs)
  session.graph.add_target(target)
  return target


def runtarget(target, *args, inputs=(), outputs=(), **kwargs):
  """
  Simplification of :func:`gentarget` to make it more obvious that a
  generate target is actually executed.
  """

  name = gtn(kwargs.pop('name', None))
  kwargs.setdefault('explicit', True)
  return gentarget([[target] + list(args)], inputs, outputs, name=name, **kwargs)


def write_response_file(arguments, builder=None, name=None, force_file=False):
  """
  Creates a response-file with the specified *name* in the in the
  ``buildfiles/`` directory and writes the *arguments* list quoted into
  the file. If *builder* is specified, it must be a :class:`TargetBuilder`
  and the response file will be added to the implicit dependencies.

  If *force_file* is set to True, a file will always be written. Otherwise,
  the function will into possible limitations of the platform and decide
  whether to write a response file or to return the *arguments* as is.

  Returns a tuple of ``(filename, arguments)``. If a response file is written,
  the returned *arguments* will be a list with a single string that is the
  filename prepended with ``@``. The *filename* part can be None if no
  response file needed to be exported.
  """

  if not name:
    if not builder:
      raise ValueError('builder must be specified if name is bot')
    name = builder.name + '.response.txt'

  if platform.name != 'win':
    return None, arguments

  # We'll just assume that there won't be more than 2048 characters for
  # other flags. The windows max buffer size is 8192.
  content = shell.join(arguments)
  if len(content) < 6144:
    return None, arguments

  filename = buildlocal(path.join('buildfiles', name))
  if builder:
    builder.implicit_deps.append(filename)

  if session.builddir:
    path.makedirs(path.dirname(filename))
    with open(filename, 'w') as fp:
      fp.write(content)
  return filename, ['@' + filename]


def error(*message):
  """
  Raises a :class:`ModuleError`.
  """

  raise ModuleError(' '.join(map(str, message)))


def append_PATH(*paths):
  """
  This is a helper function that is used to generate a ``PATH`` environment
  variable from the value that already exists and add the specified *paths*
  to it. It is typically used for example like this:

  .. code:: python

    run = gentarget(
      commands = [[main, local('example.ini')]],
      explicit=True,
      environ = {'PATH': append_PATH(qt5.bin_dir if qt5 else None)}
    )
  """

  result = _os.getenv('PATH')
  paths = _os.path.pathsep.join(filter(bool, paths))
  if paths:
    result += _os.path.pathsep + paths
  return result

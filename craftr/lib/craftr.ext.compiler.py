# -*- mode: python -*-
# Copyright (C) 2016  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
'''
This module provides common utility functions that are used by compiler
interface implementations, for example to convert source filenames to
object filenames using :meth:`gen_objects`.

Functions
---------

.. autofunction:: detect_compiler
.. autofunction:: gen_output
.. autofunction:: gen_objects
.. autofunction:: remove_flags

Exceptions
----------

.. autoclass:: ToolDetectionError
'''

__all__ = ['detect_compiler', 'gen_output', 'gen_objects',
           'remove_flags', 'ToolDetectionError', 'BaseCompiler']

from craftr import *
import collections


class ToolDetectionError(Exception):
  ''' This exception is raised if a command-line tool could not be
  successfully be detected. '''


def detect_compiler(program, language):
  ''' Detects the compiler interface based on the specified *program*
  assuming it is used for the specified *language*. Returns the detected
  compiler or raises `ToolDetectionError`. Supports all available compiler
  toolset implementations. '''

  from . import llvm, gcc, msvc

  for module in [llvm, gcc, msvc]:
    try:
      desc = module.detect(program)
    except ToolDetectionError:
      pass
    else:
      return module.Compiler(program, language, desc)

  raise ToolDetectionError('could not detect toolset for {0!r}'.format(program))


def gen_output(output, output_dir='.', suffix=None):
  output_dir = path.buildlocal(output_dir)
  if isinstance(output, str):
    if not path.isabs(output):
      output = path.join(output_dir, output)
    if suffix is not None:
      if callable(suffix):
        output = suffix(output)
      else:
        output = path.addsuffix(output, suffix)
    return output
  elif isinstance(output, collections.Iterable):
    return [gen_output(x, output_dir, suffix) for x in output]
  else:
    raise TypeError('expected str or Iterable')


def gen_objects(sources, output_dir='obj', suffix=None):
  if not sources:
    return []
  # Make sure the basedir is either the project directory or
  # only one subdir of the project directory.
  basedir = path.commonpath(sources)
  rel = path.relpath(basedir, module.project_dir, only_sub=True)
  if not path.isabs(rel):
    parts = path.split_parts(rel)[:1]
    basedir = path.join(module.project_dir, *parts)

  output_dir = path.buildlocal(output_dir)
  objects = path.move(sources, basedir, output_dir)
  if suffix is not None:
    if callable(suffix):
      objects = [suffix(path.rmvsuffix(x)) for x in objects]
    else:
      objects = path.setsuffix(objects, suffix)
  return objects


def remove_flags(command, remove_flags, builder=None):
  """
  Helper function to remove flags from a command.

  :param command: A list of command-line arguments.
  :param remove_flags: An iterable of flags to remove.
  :param builder: Optionally, a :class:`craftr.TargetBuilder`
    that will be used for logging.
  :return: The "command" list, but it is also directly altered.
  """

  # Remove the specified flags and keep every flag that could not
  # be removed from the command.
  remove_flags = set(remove_flags)
  for flag in list(remove_flags):
    count = 0
    while True:
      try:
        command.remove(flag)
      except ValueError:
        break
      count += 1
    if count != 0:
      remove_flags.remove(flag)
  if remove_flags:
    fmt = ' '.join(shell.quote(x) for x in remove_flags)
    if builder:
      builder.log('warn', "flags not removed: {0}".format(fmt))
    else:
      warn("flags not removed: {0}".format(fmt))

  return command


from .base import BaseCompiler ## backwards compatibility

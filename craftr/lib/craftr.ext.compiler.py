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

:Submodules:

.. toctree::
  :maxdepth: 2

  compiler_csc
  compiler_cython
  compiler_flex
  compiler_gcc
  compiler_java
  compiler_llvm
  compiler_msvc
  compiler_nvcc
  compiler_protoc
  compiler_yacc
'''

__all__ = ['detect_compiler', 'gen_output_dir', 'gen_output', 'gen_objects',
  'BaseCompiler', 'ToolDetectionError']

from craftr import *

import collections
import copy


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


def gen_output_dir(output_dir):
  ''' Given an output directory that is a relative path, it will be
  prefixed with the current modules' project name. An absolute path is
  left unchanged. If None is given, the current working directory is
  returned. '''

  if output_dir is None:
    output_dir = '.'
  else:
    if not path.isabs(output_dir):
      output_dir = path.join(module.project_name, output_dir)
  return output_dir


def gen_output(output, output_dir='', suffix=None):
  output_dir = gen_output_dir(output_dir)
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
  basedir = path.commonpath(sources)
  output_dir = gen_output_dir(output_dir)
  objects = path.move(sources, basedir, output_dir)
  if suffix is not None:
    if callable(suffix):
      objects = [suffix(path.rmvsuffix(x)) for x in objects]
    else:
      objects = path.setsuffix(objects, suffix)
  return objects


class BaseCompiler(object):
  ''' Base class for implementing a compiler object that can be forked
  with new options and that makes it easy to implement rule methods. '''

  def __init__(self, **kwargs):
    if not hasattr(self, 'name'):
      raise TypeError('{0}.name is not set'.format(type(self).__name__))
    super().__init__()
    self.settings = Framework(type(self).__name__, **kwargs)
    self.frameworks = [self.settings]

  def builder(self, inputs, frameworks, kwargs, **_add_kwargs):
    ''' Creates a `TargetBuilder` that also contains the frameworks of
    this compiler object. '''

    frameworks = self.frameworks + list(frameworks)
    return TargetBuilder(inputs, frameworks, kwargs, stacklevel=2, **_add_kwargs)

  def fork(self, **kwargs):
    ''' Create a fork of the compiler while overriding the *kwargs*. '''

    obj = copy.copy(self)
    # Create a new Settings framework for the compiler.
    obj.settings = Framework(type(self).__name__, **kwargs)
    # Copy the frameworks of the parent.
    obj.frameworks = self.frameworks[:]
    obj.frameworks.append(obj.settings)
    return obj

  def __getitem__(self, key):
    return FrameworkJoin(*self.frameworks)[key]

  def __setitem__(self, key, value):
    self.settings[key] = value


class ToolDetectionError(Exception):
  ''' This exception is raised if a command-line tool could not be
  successfully be detected. '''

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

__all__ = ['get_class_files', 'JavaCompiler']

from craftr import *
import re

build_dir = 'java'


def get_class_files(sources, source_dir, output_dir):
  classes = []
  for fn in sources:
    assert fn.endswith('.java')
    classes.append(path.join(output_dir, path.relpath(fn, source_dir)))
  return path.setsuffix(classes, '.class')


class JavaCompiler(object):
  ''' Class for compiling Java source files using the java compiler. '''

  def __init__(self, javac='javac', jar='jar'):
    super().__init__()
    self.javac = javac
    self.jar = jar

  def get_version(self):
    ''' Returns a tuple of `(name, version)`. '''

    output = shell.pipe([self.javac, '-version']).output
    return [x.strip() for x in output.split(' ')]

  def compile(self, source_dir, sources=None, debug=False, warn=True, classpath=(),
      additional_flags=()):
    if not sources:
      sources = path.glob(path.join(source_dir, '**/*.java'))
    outputs = get_class_files(sources, source_dir, build_dir)

    command = [self.javac, '-d', build_dir, '$in']
    command += ['-g'] if debug else []
    command += [] if warn else ['-nowarn']
    for fn in expand_inputs(classpath):
      command += ['-cp', fn]
    command += additional_flags

    return Target(command, sources, outputs)

  def make_jar(self, filename, classes, entry_point=None):
    filename = path.normpath(filename, module.project_name)
    filename = path.addsuffix(filename, '.jar')
    flags = '-cf'
    if entry_point:
      flags += 'e'
    command = [self.jar, flags, filename]
    if entry_point:
      command += [entry_point]
    command += ['-C', build_dir]
    classes = expand_inputs(classes)
    command += path.move(classes, build_dir, '')
    return Target(command, classes, [filename])

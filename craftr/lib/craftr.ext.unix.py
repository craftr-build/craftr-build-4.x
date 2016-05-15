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

__all__ = ['Ar', 'Ld', 'Objcopy', 'pkg_config']

from craftr import *
from craftr.ext import platform
from craftr.ext.compiler import BaseCompiler, gen_output, gen_objects
import re


class Ar(BaseCompiler):
  ''' Interface for the Unix `ar` archiver. '''

  name = 'Unix AR'

  def __init__(self, program='ar', **kwargs):
    super().__init__(program=program, **kwargs)

  def staticlib(self, output, inputs, target_name=None, meta=None, **kwargs):
    '''
    Supported options:

      * program
      * ar_additional_flags -- A string of additional flags (not a list!)

    Target meta variables:

      * staticlib_output -- The output filename of the library operation.
    '''

    builder = self.builder(inputs, [], kwargs, name=target_name, meta=meta)
    output = gen_output(output, suffix=platform.lib)
    flags = ''.join(utils.unique('rcs' + ''.join(builder.merge('ar_additional_flags'))))
    command = [builder['program'], flags, '$out', '$in']
    builder.meta['staticlib_output'] = output
    return builder.create_target(command, outputs=[output])


class Ld(BaseCompiler):
  ''' Interface for the Unix `ld` command. '''

  name = 'Unix LD'

  def __init__(self, program='ld', **kwargs):
    super().__init__(program=program, **kwargs)

  def link(self, output, inputs, frameworks=(), target_name=None, meta=None, **kwargs):
    '''
    Supported options:

      * program
      * linker_script

    Target meta variables:

      * link_output -- The output filename of the link operation.
    '''

    builder = self.builder(inputs, frameworks, kwargs, name=target_name, meta=meta)
    if not path.isabs(output):
      output = gen_output(output)  # xxx: suffix?

    linker_script = builder.get('linker_script', None)

    command = [join['program'], '$in', '-o', '$out']
    command += ['-T', linker_script] if linker_script else []

    builder.meta['link_output'] = output
    return builder.create_target(command, outputs=[output])


class Objcopy(BaseCompiler):
  ''' Interface for the `objcopy` tool. '''

  name = 'Unix Objcopy'

  def __init__(self, program='objcopy', detect=True, **kwargs):
    super().__init__(program=program, **kwargs)
    if detect:
      self.supported_targets = []
      stdout = shell.pipe([program, '--help']).stdout
      match = re.search(r'supported\s+targets:(.*)$', stdout, re.M)
      if match:
        self.supported_targets = match.group(1).split()
    else:
      self.supported_targets = None

  def objcopy(self, output_format, inputs, outputs=None, target_name=None,
      output_dir='', meta=None, **kwargs):
    ''' Performs an objcopy task with an output file (no append!) given the
    specified *inputs* generating *outputs* with the specified *output_format*.
    If *outputs* is omitted, it will be automatically generated from *inputs*.

    Supported options:

      * program
      * output_suffix
      * input_format
      * binary_architecture
      * description

    Target meta variables: *none*
    '''

    builder = self.builder(inputs, [], kwargs, name=target_name, meta=meta)

    # xxx: I don't think that [:3] is the correct way to derive the suffix. :)
    output_suffix = '.' + builder.get('output_suffix', output_format[:3])
    input_format = builder.get('input_format', None)
    binary_architecture = builder.get('binary_architecture', None)
    builder.target['description'] = builder.get('description', None)

    if self.supported_targets is not None:
      if output_format not in self.supported_targets:
        raise ValueError('unsupported output_format: {0}'.format(output_format))
      if input_format is not None and input_format not in self.supported_targets:
        raise ValueError('unsupported input format: {0}'.format(input_format))

    command = [builder['program']]
    command += ['-I', input_format] if input_format else []
    command += ['-B', binary_architecture] if binary_architecture else []
    command += ['-O', output_format, '$in', '$out']

    if outputs is None:
      outputs = gen_objects(builder.inputs, output_dir=output_dir, suffix=output_suffix)
    return builder.create_target(command, outputs=outputs, foreach=True)


def pkg_config(*flags):
  ''' Calls `pkg-config` with the specified flags and returns a list of
  the returned flags. '''

  command = ['pkg-config']
  command += flags
  stdout = shell.pipe(command, shell=True).stdout
  return shell.split(stdout)

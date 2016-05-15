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

__all__ = ['NvccCompiler']

from os import environ
from craftr import *
from craftr.ext import platform
from craftr.ext.compiler import gen_objects

class NvccCompiler(object):
  ''' Interface for the NVIDIA CUDA compiler. Uses the environment
  variable ``CUDA_PATH`` to determine the CUDA toolkit location.

  .. important:: This has been tested on Windows only, yet.
  '''

  def __init__(self):
    super().__init__()
    # xxx: is this cross platform compatible or does it work only on Windows?
    if 'CUDA_PATH' not in environ:
      print('craftr: warn: [compiler.nvcc.NvccCompiler] CUDA_PATH not in environment')
      self.toolkit_path = None
      self.include = []
      self.program = 'nvcc'
    else:
      self.toolkit_path = environ['CUDA_PATH']
      self.include = [path.join(self.toolkit_path, 'include')]
      self.program = path.join(self.toolkit_path, 'bin', 'nvcc')
      if platform.name == 'Windows':
        self.program = path.addsuffix(self.program, '.exe')

  def _get_libpath(self, arch):
    # xxx: can the arch be anything else then 32 and 64 bit? (amd64, x86_amd64, i386 etc. ?)
    assert arch in (32, 64)
    if not self.toolkit_path:
      return []
    if platform.name == 'Windows':
      dirname = 'Win32' if arch == 32 else 'x64'
      return [path.join(self.toolkit_path, 'lib', dirname)]
    else:
      raise NotImplementedError("can't figure nvcc toolkit library dir")

  def get_opencl_framework(self, arch=64):
    return Framework('nvidia.opencl_{0}'.format(arch), {
      'libpath': self._get_libpath(arch),
      'include': self.include,
      'libs': ['OpenCl'],
    })

  get_opencl_context = get_opencl_framework  # backwards compat

  def compile(self, sources, machine=64, static=True):
    if machine not in (32, 64):
      raise ValueError('invalid machine value: {0}'.format(machine))
    sources = expand_inputs(sources)
    objects = gen_objects(sources, suffix=platform.obj)
    command = [self.program, '-c', '$in', '-o', '$out', '--machine', str(machine)]

    fw = Framework('nvcc.NvccCompiler.compile',
      libpath = self._get_libpath(machine),
      libs = ['cuda', 'cudadevrt', 'nvcuvid', 'OpenCL',
          'cudart' + ('_static' if static else '')],
    )
    return Target(command, sources, objects, frameworks=[fw])

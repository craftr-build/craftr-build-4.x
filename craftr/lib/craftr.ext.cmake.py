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
"""
CMake-style file configuration.

.. code:: python

  from craftr import path
  from craftr.ext import cmake

  cvconfig = cmake.configure_file(
    input = path.local('cmake/templates/cvconfig.h.in'),
    environ = {
      'BUILD_SHARED_LIBS': True,
      'CUDA_ARCH_BIN': '...',
      # ...
    }
  )

  info('cvconfig.h created in', cvconfig.include)

Functions
---------

.. autofunction:: configure_file

Classes
-------

.. autoclass:: ConfigResult
"""

__all__ = ['ConfigResult', 'configure_file']

from craftr import *
from craftr.ext.compiler import gen_objects

import craftr
import re
import string

#: Result of a CMake configuration. Contains the :attr:`filename`,
#: a list of :attr:`include` directories and the :class:`target` if
#: one was generated.
ConfigResult = utils.recordclass('ConfigResult', 'output include target')


def configure_file(input, output=None, environ={}, inherit_environ=True):
  """
  Renders the CMake configuration file using the specified environment
  and optionally the process' environment.

  If the *output* parameter is omitted, an output filename in a
  special ``include/`` directory will be generated from the *input*
  filename. The ``.in`` suffix from *input* will be removed if it
  exists.

  :param input: Absolute path to the CMake config file.
  :param output: Name of the output file. Will be automatically
    generated if omitted.
  :param environ: A dictionary containing the variables for
    rendering the CMake configuration file. Non-existing
    variables are considered undefined.
  :param inherit_environ: If True, the environment variables of the
    Craftr process are additionally taken into account.
  :return: A :class:`ConfigResult` object.
  """

  if not output:
    output = gen_objects([input],  'include')[0]
    if output.endswith('.in'):
      output = output[:-3]

  if inherit_environ:
    new_env = craftr.environ.copy()
    new_env.update(environ)
    environ = new_env
    del new_env

  output_dir = path.dirname(output)

  if session.export:
    path.makedirs(output_dir)

    with open(input) as src:
      with open(output, 'w') as dst:
        for line in src:
          match = re.match('\s*#cmakedefine\s+(\w+)\s*(.*)', line)
          if match:
            var, value = match.groups()
            if variables.get(var, False):
              line = '#define {} {}\n'.format(var, value)
            else:
              line = '/* #undef {} */\n'.format(var)

          # Replace variable references with $X or ${X}
          def replace(match):
            value = variables.get(match.group(3), None)
            if value:
              return str(value)
            return ''
          line = string.Template.pattern.sub(replace, line)

          dst.write(line)

  return ConfigResult(output, output_dir, None)

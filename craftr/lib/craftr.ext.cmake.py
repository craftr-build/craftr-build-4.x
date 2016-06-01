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
This module allows you to render CMake configuration headers from Craftr
(without using CMake at all).

.. code:: python

  from craftr import path
  from craftr.ext import cmake
  config = cmake.render_config(
    config_file = path.local('cmake/templates/cvconfig.h.in'),
    variables = {
      'BUILD_SHARED_LIBS': True,
      'CUDA_ARCH_BIN': '...',
      # ...
    }
  )
  include = config.include + path.glob('modules/*/include')
"""

__all__ = ['ConfigResult', 'render_config']

from craftr import session, environ, Framework, task, path, utils
from craftr.ext.compiler import gen_objects

import re
import string

#: Result of a CMake configuration. Contains the :attr:`filename`,
#: a list of :attr:`include` directories and the :class:`target` if
#: one was generated.
ConfigResult = utils.slotobject('ConfigResult', 'filename include target')


def render_config(config_file, output=None, variables={}, inherit_env=True):
  '''
  Render a CMake *config_file* given the specified *variables*
  dictionary. If *output* is None, the output filename will
  automatically be generated in the current project's build
  directory.

  :param config_file: Absolute path to the CMake config file.
  :param output: Path to the output file, or None to create
    the output filename automatically.
  :param variables: A dictionary containing the variables for
    rendering the CMake configuration file. Non-existing
    variables are considered undefined.
  :param inherit_env: Inherit environment variables in
    *variables*. The default is True.
  :return: :class:`ConfigResult`
  '''

  if not output:
    output = gen_objects([config_file],  'include')[0]
    if output.endswith('.in'):
      output = output[:-3]

  if inherit_env:
    temp = variables
    variables = dict(environ)
    variables.update(temp)
    del temp

  output_dir = path.dirname(output)

  if session.export:
    path.makedirs(output_dir)

    with open(config_file) as src:
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

  return ConfigResult(output, [output_dir], None)

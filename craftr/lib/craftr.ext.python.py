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
This Craftr extension module provides information about Python
installations that are required for compiling C-extensions. Use
the :func:`get_python_framework` function to extract all the
information from a Python installation using its ``distutils``
module.
'''

__all__ = ['get_python_config_vars', 'get_python_framework']

from craftr import *
from craftr.ext import platform
import json, re



@memoize_tool
def get_python_config_vars(python_bin):
  ''' Given the name or path to a Python executable, this function
  returns the dictionary that would be returned by
  ``distutils.sysconfig.get_config_vars()``. '''

  pyline = 'import json, distutils.sysconfig; '\
    'print(json.dumps(distutils.sysconfig.get_config_vars()))'

  output = shell.pipe([python_bin, '-c', pyline], shell=True).output
  return json.loads(output)


def get_python_framework(python_bin):
  ''' Uses :func:`get_python_config_vars` to read the configuration
  values and returns a :class:`Framework` from that data that exposes
  the following options:

  :ivar include: List of include paths (derived from ``INCLUDEPY``)
  :ivar libpath: List of library paths (derived from ``LIBDIR``)
  '''

  config = get_python_config_vars(python_bin)
  # LIBDIR seems to be absent from Windows installations, so we
  # figure it from the prefix.
  if platform.name == 'win' and 'LIBDIR' not in config:
    config['LIBDIR'] = path.join(config['prefix'], 'libs')

  fw = Framework(python_bin,
    include = [config['INCLUDEPY']],
    libpath = [config['LIBDIR']],
  )

  # The name of the Python library is something like "libpython2.7.a",
  # but we only want the "python2.7" part. Also take the library flags
  # m, u and d into account (see PEP 3149).
  if 'LIBRARY' in config:
    lib = re.search('python\d\.\d(?:d|m|u){0,3}', config['LIBRARY'])
    if lib:
      fw['libs'] = [lib.group(0)]

  return fw

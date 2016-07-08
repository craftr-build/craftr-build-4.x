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
This module represents the current platform that Craftr is running on by
importing the correct implementation based on :data:`sys.platform`. Be
sure to check out the :ref:`platform_interface` documentation.


Platform C/C++ Toolset
----------------------

.. data:: asm

  The Assembler retrieved with :func:`platform.get_tool`

.. data:: cc

  The C compiler retrieved with :func:`platform.get_tool`

.. data:: cxx

  The C++ compiler retrieved with :func:`platform.get_tool`

.. data:: ld

  The linker retrieved with :func:`platform.get_tool`

.. data:: ar

  The archiver retrieved with :func:`platform.get_tool`

Constants
---------

.. autodata:: WIN32
.. autodata:: DARWIN
.. autodata:: LINUX
.. autodata:: CYGWIN
'''

__all__ = ['WIN32', 'DARWIN', 'LINUX', 'CYGWIN', 'asm', 'cc', 'cxx', 'ld', 'ar']

from craftr import import_module, environ
import sys

WIN32 = 'win'     #: Windows platform name
DARWIN = 'mac'    #: Mac OS platform name
LINUX = 'linux'   #: Linux platform name
CYGWIN = 'cygwin' #: Cygwin platform name

# Wildcard-import the module for the current platform.
import_module(__name__ + '.' + sys.platform, globals(), '*')

# get_tool() imported from the current platform module.
if 'SPHINXBUILD' not in environ:
  asm = get_tool('asm')
  cc = get_tool('cc')
  cxx = get_tool('cxx')
  ld = get_tool('ld')
  ar = get_tool('ar')

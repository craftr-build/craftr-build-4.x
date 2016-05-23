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
''' This module represents the current platform that Craftr is running
on by importing the correct implementation based on :data:`sys.platform`.

Available Implementations
-------------------------

.. toctree::
  :maxdepth: 2

  platform_cygwin
  platform_darwin
  platform_linux
  platform_win32

Contents
--------
'''

__all__ = ['WIN32', 'DARWIN', 'LINUX', 'CYGWIN', 'cc', 'cxx', 'ld', 'ar']

from craftr import import_module
from craftr.magic import Proxy
import sys

WIN32 = 'win'     #: Windows platform name
DARWIN = 'mac'    #: Mac OS platform name
LINUX = 'linux'   #: Linux platform name
CYGWIN = 'cygwin' #: Cygwin platform name

# Wildcard-import the module for the current platform.
import_module(__name__ + '.' + sys.platform, globals(), '*')

# get_tool() imported from the current platform module.
cc = Proxy(get_tool, 'cc')    #: The C compiler retrieved with :func:`platform.get_tool`
cxx = Proxy(get_tool, 'cxx')  #: The C++ compiler retrieved with :func:`platform.get_tool`
ld = Proxy(get_tool, 'ld')    #: The linker retrieved with :func:`platform.get_tool`
ar = Proxy(get_tool, 'ar')    #: The archiver retrieved with :func:`platform.get_tool`

# The Craftr build system
# Copyright (C) 2016  Niklas Rosenstein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Platform MSYS2 and Cygwin.
"""

from craftr.utils import path

import os
import sys


def _check():
  """
  Checks if we're in a Cygwin or MSYS2 environment. Returns the name, i.e.
  either ``'cygwin'`` or ``'msys'``, or None if we're currently in neither of
  the two environments.
  """

  if sys.platform.startswith('cygwin'):
    return 'cygwin'
  elif sys.platform.startswith('msys'):
    return 'msys'
  elif sys.platform.startswith('win32'):
    if os.path.sep == '/':
      return 'msys'
  return None


name = _check()
standard = "posix"

def obj(x): return path.addsuffix(x, ".obj")
def bin(x): return path.addsuffix(x, ".exe")
def dll(x): return path.addsuffix(x, ".dll")
def lib(x): return path.addsuffix(x, ".lib")

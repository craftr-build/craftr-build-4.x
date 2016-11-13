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

import sys

if sys.platform.startswith('cygwin'):
  name = "cygwin"
  standard = "posix"

  def obj(x): return path.addsuffix(x, ".obj")
  def bin(x): return path.addsuffix(x, ".exe")
  def dll(x): return path.addsuffix(x, ".dll")
  def lib(x): return path.addsuffix(x, ".lib")

elif sys.platform.startswith('darwin'):
  name = "mac"
  standard = "posix"

  def obj(x): return path.addsuffix(x, ".o")
  def bin(x): return x
  def dll(x): return path.addsuffix(x, ".dylib")
  def lib(x): return path.addprefix(path.addsuffix(x, ".a"), "lib")

elif sys.platform.startswith('linux'):
  name = "linux"
  standard = "posix"

  def obj(x): return path.addsuffix(x, ".o")
  def bin(x): return x
  def dll(x): return path.addsuffix(x, ".so")
  def lib(x): return path.addprefix(path.addsuffix(x, ".a"), "lib")

elif sys.platform.startswith('win32'):
  name = "win"
  standard = "nt"

  def obj(x): return path.addsuffix(x, ".obj")
  def bin(x): return path.addsuffix(x, ".exe")
  def dll(x): return path.addsuffix(x, ".dll")
  def lib(x): return path.addsuffix(x, ".lib")

else:
  raise EnvironmentError('unsupported platform: {}'.format(sys.platform))

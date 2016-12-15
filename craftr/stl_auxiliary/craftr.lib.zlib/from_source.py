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

options.url = options.url.replace('${VERSION}', options.version)
if not options.directory:
  options.directory = external_archive(options.url)

zlib = Framework(
  include = [options.directory],
  defines = []
)

if platform.name == 'win':
  zlib['defines'].append('ZLIB_WINAPI')
if not options.static:
  zlib['defines'].append('ZLIB_DLL')

cxx = load_module('craftr.lang.cxx')

lib = cxx.library(
  link_style = 'static' if options.static else 'shared',
  inputs = cxx.c_compile(
    sources = glob(['*.c'], parent = options.directory),
    source_directory = options.directory,
    frameworks = [zlib],
    defines = [],
    pic = not options.static
  ),
  output = 'zlib',
  name = 'zlib'
)

cxx.extend_framework(zlib, lib)

if options.build_examples:
  examples = ['example', 'minigzip']
  if platform.name != 'win':
    # infcover uses reallocf() which is not available on Windows
    examples.append('infcover')

  for name in examples:
    target = cxx.binary(
      output = name,
      inputs = cxx.c_compile(
        sources = [path.join(options.directory, 'test', name + '.c')],
        source_directory = options.directory,
        frameworks = [zlib],
        name = name + '_compile'
      ),
      name = name
    )

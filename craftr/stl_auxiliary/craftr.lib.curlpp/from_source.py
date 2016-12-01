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

options = session.module.options
from craftr.loaders import external_archive

source_directory = external_archive(
  "https://github.com/jpbarrette/curlpp/archive/{}.zip".format(options.version)
)

if options.static:
  session.options.setdefault('craftr.lib.curl.static', True)
else:
  session.options.setdefault('craftr.lib.curl.static', False)

load_module('craftr.lang.cxx.*')

cURL = load_module('craftr.lib.curl').cURL
cURLpp = Framework('cURLpp',
  include = [path.join(source_directory, 'include')],
  defines = [],
  frameworks = [cURL]
)

if options.static:
  cURLpp['defines'] += ['CURLPP_STATICLIB']

cURLpp_library = cxx_library(
  link_style = 'static' if options.static else 'shared',
  inputs = cpp_compile(
    sources = glob(['src/**/*.cpp'], parent = source_directory),
    frameworks = [cURLpp],
    defines = ['BUILDING_CURLPP'],
    rtti = options.rtti
  ),
  output = 'cURLpp'
)

cxx_extend_framework(cURLpp, cURLpp_library)


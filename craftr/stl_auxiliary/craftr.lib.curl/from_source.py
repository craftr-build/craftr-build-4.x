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

# Framework that is used by other libraries/applications.
cURL = Framework(
  include = [],
  defines = ['CURL_STATICLIB'] if options.static else [],
  libs = []
)

# Framework for building libcURL.
cURL_building = Framework(
  frameworks = [cURL],
  defines = ['BUILDING_LIBCURL'],
  include = []
)

# Platform dependent settings.
if platform.name == 'win':
  cURL['libs'] += 'kernel32 user32 gdi32 winspool shell32 ole32 oleaut32 uuid comdlg32 advapi32 wldap32 winmm ws2_32 crypt32'.split()
  cURL_building['defines'] += ['HAVE_CONFIG_H', '_WIN32_WINNT=0x0501']
  # Note: Yes, a bit hacky. Workaround until we can either maybe evaluate
  # CMake files or have CMake like feature checks (see craftr-build/craftr#134).
  cURL_building['include'] += [local('windows')]
else:
  # TODO
  error('platform currently not supported: {}'.format(platform.name))

# Grab the cURL source and update the include directory in the public framework.
source_directory = external_archive(
  "https://curl.haxx.se/download/curl-{}.tar.gz".format(options.version)
)
cURL['include'] += [path.join(source_directory, 'include')]

# Compile the library.
cxx = load('craftr.lang.cxx')
libcURL = cxx.library(
  link_style = 'static' if options.static else 'shared',
  inputs = cxx.compile_c(
    sources = glob(['src/**/*.c', 'lib/**/*.c'], parent = source_directory),
    include = [path.join(source_directory, 'lib')],
    frameworks = [cURL, cURL_building]
  ),
  output = 'cURL'
)

cxx.extend_framework(cURL, libcURL)

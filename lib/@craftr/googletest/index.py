
import os
import craftr from 'craftr'
import cxx from '@craftr/cxx'

version = craftr.options.get('googletest.version', '1.8.0')
if not version.startswith('release-'):
  version = 'release-' + version
directory = craftr.get_source_archive(craftr.fmt("https://github.com/google/googletest/archive/{version}.zip"))
directory = craftr.path.abs(craftr.path.join(directory, 'googletest-' + version))

cxx.library(
  name = 'googletest',
  cpp_std = 'c++11',
  srcs = [
    craftr.path.join(directory, 'googlemock/src/gmock-all.cc'),
    craftr.path.join(directory, 'googletest/src/gtest-all.cc')
  ],
  includes = [
    craftr.path.join(directory, 'googlemock'),
    craftr.path.join(directory, 'googletest')
  ],
  exported_includes = [
    craftr.path.join(directory, 'googlemock/include'),
    craftr.path.join(directory, 'googletest/include')
  ],
  exported_syslibs = [] if os.name == 'nt' else ['pthread'],
  preferred_linkage = 'static'
)

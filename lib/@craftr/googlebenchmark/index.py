
import os
import craftr from 'craftr'
import cxx from '@craftr/cxx'

version = craftr.options.get('googlebenchmark.version', 'v1.1.0')
regex_backend = craftr.options.get('googlebenchmark.regex_backend', 'std')
directory = craftr.get_source_archive(craftr.fmt("https://github.com/google/benchmark/archive/{version}.zip"))
directory = craftr.path.abs(craftr.path.join(directory, 'benchmark-' + version.lstrip('v')))

defines = []
if regex_backend == 'std':
  defines.append('HAVE_STD_REGEX')
elif regex_backend == 'gnu':
  defines.append('HAVE_GNU_POSIX_REGEX')
elif regex_backend == 'posix':
  defines.append('HAVE_POSIX_REGEX')
else:
  raise EnvironmentError('invalid googlebenchmark.regex_backend value: {!r}'
      .format(regex_backend))
if os.name == 'nt':
  defines.append('_CRT_SECURE_NO_WARNINGS')

cxx.library(
  name = 'googlebenchmark',
  cpp_std = 'c++11',
  srcs = craftr.glob('src/*.cc', parent=directory),
  defines = defines,
  exported_includes = [
    craftr.path.join(directory, 'include'),
  ],
  exported_syslibs = ['Shlwapi'] if os.name == 'nt' else ['pthread'],
  preferred_linkage = 'static'
)

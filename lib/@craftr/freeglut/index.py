
import sys
import craftr, {path} from 'craftr'
import {configure_file} from '@craftr/cmake'
import cxx from '@craftr/cxx'

binary_dir = craftr.options.get('freeglut.binary_dir', None)
static = craftr.options.get('freeglut.static', True)

if binary_dir:
  cxx.prebuilt(
    name = 'freeglut',
    include = [path.join(binary_dir, 'include')],
    libpath = [path.join(binary_dir, 'lib/x64' if cxx.compiler.is64bit else 'lib')],
    syslibs = ['freeglut_static' if static else 'freeglut']
  )
else:
  if sys.platform.startswith('win32'):
    platform = 'mswin'
  elif sys.platform.startswith('linux'):
    platform = 'x11'
  else:
    raise EnvironmentError('unsupported platform to compile from source: {!r}'.format(platform))
  binary_dir = craftr.get_source_archive('https://github.com/dcnieho/FreeGLUT/archive/FG_3_0_0.zip')
  binary_dir = path.join(path.abs(binary_dir), 'FreeGLUT-FG_3_0_0')

  environ = {
    'VERSION_MAJOR': '3',
    'VERSION_MINOR': '0',
    'VERSION_PATCH': '0'
  }

  sources = craftr.glob(['src/*.c', 'src/{}/*.c'.format(platform)], parent=binary_dir)
  syslibs = []
  defines = ['HAVE_CONFIG_H', 'FREEGLUT_BUILDING_LIB']
  exported_defines = ['FREEGLUT_STATIC'] if static else []
  exported_defines += ['FREEGLUT_LIB_PRAGMAS=0']
  if platform != 'x11':
    defines += ['NEED_XPARSEGEOMETRY_IMPL']
    sources.append(path.join(binary_dir, 'src/util/xparsegeometry_repl.c'))

  compiler_options = {}

  # Configure .in files.
  if sys.platform.startswith('win32'):
    freeglut_rc = configure_file(path.join(binary_dir, 'freeglut.rc.in'), environ=environ).output
    compiler_options['msvc_resource_files'] = [freeglut_rc]
    compiler_options['msvc_disable_warnings'] = [
      '4100',  # unreferenced formal parameter
      '4127',  # conditional expression is constant
    ]
    syslibs += [
      'glu32',
      'opengl32',
      'gdi32',
      'winmm',
      'user32',
      'advapi32'
    ]
  config_h_in = configure_file(path.join(binary_dir, 'config.h.in'), environ=environ).directory

  cxx.library(
    name = 'freeglut',
    exported_includes = [path.join(binary_dir, 'include'), config_h_in],
    defines = defines,
    exported_defines = exported_defines,
    exported_syslibs = syslibs,
    srcs = sources,
    options = compiler_options
  )


namespace = 'craftr/libs/glfw'

import os, sys
import craftr, {path, fmt} from 'craftr'
import cxx from 'craftr/lang/cxx'
import {configure_file} from 'craftr/tools/cmake'
import {pkg_config} from 'craftr/tools/pkg-config'

source_dir = craftr.options.get('glfw.source_dir')
binary_dir = craftr.options.get('glfw.binary_dir')
version = craftr.options.get('glfw.version', '3.2.1')
from_source = craftr.options.get('glfw.from_source')
msvc_version = craftr.options.get('glfw.msvc_version', None)
static = craftr.options.get('glfw.static', True)
x11 = craftr.options.get('glfw.x11', True)
wayland = craftr.options.get('glfw.wayland', True)


def define_windows_prebuilt():
  global binary_dir
  global msvc_version

  if not binary_dir:
    winver = 'WIN64' if cxx.compiler.is64bit else 'WIN32'
    url = fmt('https://github.com/glfw/glfw/releases/download/{version}/glfw-{version}.bin.{winver}.zip')
    binary_dir = craftr.get_source_archive(url.format(**locals()))
    binary_dir = path.join(path.abs(binary_dir), fmt('glfw-{version}.bin.{winver}'))

  if cxx.compiler.id == 'msvc':
    if msvc_version is None:
      msvc_version = cxx.compiler.toolkit.vs_year
    libdir = 'lib-vc{}'.format(msvc_version)
  elif cxx.compiler.id == 'mingw':
    libdir = 'lib-mingw' if cxx.compiler.is32bit else 'lib-mingw-w64'
  else: assert False, cxx.compiler.id

  cxx.prebuilt(
    name = 'glfw',
    includes = [path.join(binary_dir, 'include', 'GLFW')],
    libpath = [path.join(binary_dir, libdir)],
    syslibs = [
      'glfw3' if static else 'glfw3dll',
      'shell32'
    ]
  )


def define_pkg_config():
  pkg_config('glfw')


def define_from_source():
  global source_dir
  if not source_dir:
    url = fmt('https://github.com/glfw/glfw/releases/download/{version}/glfw-{version}.zip')
    source_dir = craftr.get_source_archive(url)
    source_dir = path.join(path.abs(source_dir), fmt('glfw-{version}'))

  sources = [path.join(source_dir, 'src', x) for x in [
    'context.c',
    'egl_context.c',
    'init.c',
    'input.c',
    'monitor.c',
    'vulkan.c',
    'window.c'
  ]]
  syslibs = []

  environ = {}
  environ['_GLFW_VULKAN_STATIC'] = False
  environ['_GLFW_USE_HYBRID_HPG'] = True
  environ['_GLFW_USE_RETINA'] = True
  if not static:
    environ['_GLFW_BUILD_DLL'] = True
  if sys.platform.startswith('win32'):
    environ['_GLFW_WIN32'] = True
    sources += craftr.glob(['src/win32_*.c', 'src/wgl_context.c'], parent=source_dir)
    syslibs += ['shell32']
  elif sys.platform.startswith('darwin'):
    environ['_GLFW_COCOA'] = True
  elif sys.platform.startswith('linux'):
    if x11 or not wayland:
      environ['_GLFW_X11'] = True
    elif wayland:
      environ['_GLFW_WAYLAND'] = True
  # TODO: _GLFW_MIR ?
  # TODO: _GLFW_HAS_XF86VM ?

  config_dir = configure_file(path.join(source_dir, 'src/glfw_config.h.in'), environ=environ).directory

  cxx.library(
    name = 'glfw',
    srcs = sources,
    includes = [config_dir],
    defines = ['_GLFW_USE_CONFIG_H'],
    exported_includes = [path.join(source_dir, 'include', 'GLFW')],
    preferred_linkage = 'static' if static else 'shared',
    exported_syslibs = syslibs
  )


if from_source:
  print('Using GLFW3 from source')
  define_from_source()
elif os.name == 'nt' and cxx.compiler.id in ('msvc', 'mingw'):
  print('Using GLFW3 Windows Prebuilt')
  define_windows_prebuilt()
else:
  print('Using GLFW3 pkg-config')
  define_pkg_config()

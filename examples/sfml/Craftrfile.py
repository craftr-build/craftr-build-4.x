
import os
import {session, glob, path} from 'craftr'
import cxx from 'craftr/lang/cxx'

sfml_directory = session.config.get('sfml.directory')
sfml_static = session.config.get('sfml.static')
sfml_debug = session.config.get('sfml.debug')
ssfx = '-s' if sfml_static else ''
dsfx = '-d' if sfml_debug else ''

sfml = cxx.prebuilt(
  name = 'sfml',
  includes = [path.join(sfml_directory, 'include')],
  defines = ['SFML_STATIC'] if sfml_static else [],
  libpath = [path.join(sfml_directory, 'lib')],
  syslibs = [x.format(**globals()) for x in [
    'sfml-main{dsfx}',
    'sfml-system{ssfx}{dsfx}',
    'sfml-audio{ssfx}{dsfx}',
    'sfml-graphics{ssfx}{dsfx}',
    'sfml-network{ssfx}{dsfx}',
    'sfml-window{ssfx}{dsfx}',
    'opengl32',
    'openal32',
    'freetype',
    'jpeg',
    'flac',
    'vorbisenc',
    'vorbisfile',
    'vorbis',
    'ogg'
  ]]
)

if os.name == 'nt':
  sfml.data.syslibs += [
    'ws2_32',
    'winmm',
    'gdi32',
    'user32',
    'advapi32'
  ]
else:
  # TODO: Are these correct?
  sfml.data.syslibs = [
    'pthread',
    'opengl',
    'xlib',
    'xrandr',
    'udev'
  ] + sfml.data.syslib


cxx.build(
  name = 'main',
  type = 'binary',
  srcs = glob('src/*.cpp'),
  deps = [':sfml']
)

cxx.run(':main')

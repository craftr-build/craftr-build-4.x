
namespace = 'cxx-opencl'

import craftr from 'craftr'
import cxx from 'craftr/lang/cxx'
import 'craftr/libs/glew'
import 'craftr/libs/glfw'
import 'craftr/libs/opencl'

cxx.embed(
  name = 'files',
  files = [craftr.localpath(x) for x in [
    'src/kernel.cl',
    'src/screen.vert',
    'src/screen.frag'
  ]],
  names = [
    'ClKernel',
    'ScreenVert',
    'ScreenFrag'
  ]
)

cxx.binary(
  name = 'main',
  deps = [
    ':files',
    '//craftr/libs/glew:glew',
    '//craftr/libs/glfw:glfw',
    '//craftr/libs/opencl:opencl'
  ],
  srcs = ['src/main.c'],
  includes = ['src/common']
)

cxx.run(':main')

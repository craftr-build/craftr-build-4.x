
namespace = 'opencl'

import craftr from 'craftr'
import cxx from '@craftr/cxx'
import '@craftr/glew'
import '@craftr/glfw'
import '@craftr/opencl'

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
    '//@craftr/glew:glew',
    '//@craftr/glfw:glfw',
    '//@craftr/opencl:opencl'
  ],
  srcs = ['src/main.c'],
  includes = ['src/common']
)

cxx.run(':main')

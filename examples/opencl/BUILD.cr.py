
namespace = 'cxx-opencl'

import craftr from 'craftr'
import cxx from 'craftr/lang/cxx'
import 'craftr/libs/glew'
import 'craftr/libs/glfw'
import 'craftr/libs/opencl'

cxx.embed(
  name = 'kernel',
  files = [craftr.localpath('src/kernel.cl')],
  names = ['Kernel']
)

cxx.binary(
  name = 'main',
  deps = [
    ':kernel',
    '//craftr/libs/glew:glew',
    '//craftr/libs/glfw:glfw',
    '//craftr/libs/opencl:opencl'
  ],
  srcs = craftr.glob(['src/*.cpp', 'src/common/*.cpp']),
  includes = ['src/common']
)

cxx.run(':main')

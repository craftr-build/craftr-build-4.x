
namespace = 'cxx-opencl'

import craftr from 'craftr'
import cxx from 'craftr/lang/cxx'
import 'craftr/libs/glew'
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
    '//craftr/libs/opencl:opencl'
  ],
  srcs = craftr.glob(['src/*.cpp', 'src/common/*.cpp']),
  includes = ['src/common'],
  options = dict(
    msvc_resource_files = ['src/OpenGLInterop.rc']
  )
)

cxx.run(':main')

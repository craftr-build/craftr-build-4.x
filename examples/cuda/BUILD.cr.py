
namespace = 'cuda'

import craftr from 'craftr'
import cuda from '@craftr/cuda'
import '@craftr/freeglut'
import '@craftr/glew'

cuda.binary(
  name = 'main',
  deps = [
    '//@craftr/glew:glew',
    '//@craftr/freeglut:freeglut'
  ],
  srcs = craftr.glob(['src/*.cpp', 'src/*.cu']),
  includes = ['include']
)

cuda.run(':main')


namespace = 'cuda-example'

import craftr from 'craftr'
import 'craftr/libs/freeglut'
import 'craftr/libs/glew'
import cuda from 'craftr/lang/cuda'

cuda.binary(
  name = 'main',
  deps = [
    '//craftr/libs/glew:glew',
    '//craftr/libs/freeglut:freeglut'
  ],
  srcs = craftr.glob(['src/*.cpp', 'src/*.cu']),
  includes = ['include']
)

cuda.run(':main')

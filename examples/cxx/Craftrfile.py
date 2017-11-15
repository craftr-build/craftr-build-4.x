
import craftr from 'craftr'
import cxx from 'craftr/lang/cxx'

cxx.build(
  name = 'lib',
  target = 'library',
  srcs = craftr.glob('src/*.c')
)

cxx.build(
  name = 'main',
  target = 'binary',
  deps = [':lib'],
  srcs = 'main.c'
)


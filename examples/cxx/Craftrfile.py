
import {gentarget, glob, t} from 'craftr'
import cxx from 'craftr/lang/cxx'

cxx.build(
  name = 'lib',
  type = 'library',
  srcs = glob('src/*.c')
)

cxx.build(
  name = 'main',
  deps = [':lib'],
  type = 'binary',
  srcs = 'main.c'
)

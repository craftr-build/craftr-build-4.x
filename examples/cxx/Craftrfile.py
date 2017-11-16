
import {gentarget, glob, t} from 'craftr'
import cxx from 'craftr/lang/cxx'

cxx.build(
  name = 'lib',
  type = 'library',
  srcs = glob('src/*.c'),
  shared_defines = ['HELLOLIB_EXPORTS'],
  exported_shared_defines = ['HELLOLIB_SHARED']
)

cxx.build(
  name = 'main',
  deps = [':lib'],
  type = 'binary',
  srcs = 'main.c',
  link_style = 'shared'
)

cxx.run(':main')

# Sample Craftr build script for C/C++ projects.

import craftr from 'craftr'
import cxx from 'craftr/lang/cxx'

cxx.library(
  name = 'lib',
  srcs = craftr.glob('src/*.c'),
  shared_defines = ['HELLOLIB_EXPORTS'],
  exported_shared_defines = ['HELLOLIB_SHARED']
)

cxx.binary(
  name = 'main',
  deps = [':lib'],
  srcs = 'main.c',
  link_style = 'shared'  # Explicitly link shared (default is static)
)

cxx.run(':main')

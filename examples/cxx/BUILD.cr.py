# Sample Craftr build script for C/C++ projects.

import craftr from 'craftr'
import cxx from 'craftr/lang/cxx'

cxx.binary(
  name = 'main',
  srcs = craftr.glob('src/*.cpp'),
  unity_build = True
)

cxx.run(':main')

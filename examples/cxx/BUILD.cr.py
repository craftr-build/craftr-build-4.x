# Sample Craftr build script for C/C++ projects.

import craftr from 'craftr'
import cxx from 'craftr/lang/cxx'

# Will be embedded into the executable, we can use this to print the build
# script that was used to build the program (see main.cpp).
cxx.embed(
  name = 'files',
  files = [craftr.localpath('BUILD.cr.py')],
  names = ['BUILDSCRIPT']
)

cxx.binary(
  name = 'main',
  deps = [':files'],
  srcs = craftr.glob('src/*.cpp'),
  cpp_std = 'c++11',
  unity_build = True
)

cxx.run(':main')

import craftr from 'craftr'
import cxx from 'craftr/lang/cxx'
import 'craftr/libs/sfml'

cxx.binary(
  name = 'main',
  deps = ['//craftr/libs/sfml:sfml'],
  srcs = ['main.cpp']
)

cxx.run(':main')

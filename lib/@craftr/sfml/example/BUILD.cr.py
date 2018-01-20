import craftr from 'craftr'
import cxx from '@craftr/cxx'
import '@craftr/sfml'

cxx.binary(
  name = 'main',
  deps = ['//sfml:sfml'],
  srcs = ['main.cpp']
)

cxx.run(':main')

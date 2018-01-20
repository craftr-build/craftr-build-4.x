# Sample Craftr build script for Java projects.

namespace = 'java'

import craftr from 'craftr'
import java from '@craftr/java'

java.prebuilt(
  name = 'libs',
  artifacts = [
    'org.tensorflow:tensorflow:1.4.0'
  ]
)

java.binary(
  name = 'main',
  deps = [':libs'],
  srcs = craftr.glob('src/**.java'),
  main_class = 'Main'
)

java.run(':main')

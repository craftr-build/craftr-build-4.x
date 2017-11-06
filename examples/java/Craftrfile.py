
import craftr from 'craftr'
import java from 'craftr/lang/java'

java.prebuilt(
  name = 'hello',
  binary_jar = 'vendor/hello-1.0.0.jar'
)

java.library(
  name = 'main_lib',
  srcs = craftr.glob('src/**.java'),
  transitive_deps = [':hello']
)

java.binary(
  name = 'main',
  deps = [':main_lib'],
  main_class = 'Main'
)

java.run(':main')


import craftr from 'craftr'
import java from 'craftr/lang/java'

java.prebuilt(
  name = 'hello',
  binary_jar = 'vendor/hello-1.0.0.jar'
)

java.prebuilt(
  name = 'guava',
  artifact = 'com.google.guava:guava:23.4-jre'
)

java.binary(
  name = 'main',
  deps = [':hello', ':guava'],
  srcs = craftr.glob('src/**.java'),
  main_class = 'Main'
)

java.run(':main')


import craftr from 'craftr'
import java from 'craftr/lang/java'

java.prebuilt(
  name = 'hello',
  binary_jar = 'vendor/hello-1.0.0.jar'
)

java.binary(
  name = 'main',
  deps = [':hello'],
  srcs = craftr.glob('src/**.java'),
  main_class = 'Main'
)

java.run(':main')

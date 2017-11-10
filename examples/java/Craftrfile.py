
import craftr from 'craftr'
import java from 'craftr/lang/java'

# Downloads Guava 23.4 from Maven Central.
java.prebuilt(name = 'guava', artifact = 'com.google.guava:guava:23.4-jre')

java.binary(
  name = 'main',
  deps = [':guava'],
  srcs = craftr.glob('src/**.java'),
  main_class = 'Main'
)

java.run(':main')

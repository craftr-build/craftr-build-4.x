## examples/java

### Demonstrates

* Build a Java library into a JAR
* Use Maven dependencies
* Bundle all dependencies into a single JAR file

### Build

    $ craftr -cb main:java.jar        # Produce the JAR file
    $ craftr -cb main:java.run        # Run the JAR

    $ craftr -cb main:java.jarBundle  # Produce the JAR bundle
    $ craftr -cb main:java.runBundle  # Run the bundled JAR

### To do

* [ ] A way to include resource files in the generated JAR

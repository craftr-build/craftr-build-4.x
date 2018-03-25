## examples/java

This example demonstrates how to build a Java project with Maven dependencies
and how Craftr can bundle all dependencies into a single JAR.

    $ craftr -cb main:java.jar        # Produce the JAR file
    $ craftr -cb main:java.run        # Run the JAR

    $ craftr -cb main:java.jarBundle  # Produce the JAR bundle
    $ craftr -cb main:java.runBundle  # Run the bundled JAR

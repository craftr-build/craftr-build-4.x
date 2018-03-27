## examples/java-mod

### Demonstrates

* Building a Java 9 module (`.jmod`)
* Creating a Java 9 standalone runtime with `jlink` from the previously
  generated Java module

### Build

    # Build the JMOD:
    $ craftr -cb main:java.jmod

    # Run the JMOD (only available when a single JMOD is created by the target)
    $ craftr -cb main:java.run
    Hello, World!

    # Or run the JMOD manually:
    $ java --module-path build/debug/examples.java-mod/main/jmods -m com.greetings/com.greetings.Main
    Hello, World!

    # Run jlink to produce a runtime with all your JMODs:
    $ craftr -cb main:java.jlink

    # Run the launcher created by jlink:
    $ build/debug/examples.java-mod/main-1.0.0-runtime/bin/greetings
    Hello, World!

### To do

* [ ] A way to include resource files in the generated JMOD

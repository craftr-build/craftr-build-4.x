## examples/java-mod

This example demonstrates how to produce a Java 9+ module and how to produce
a Java standalone runtime with the `jlink` tool.

__Building and running the Java Module__

    $ craftr -cb main:java.jmod
    $ java --module-path build/debug/examples.java-mod/main/jmods -m com.greetings/com.greetings.Main
    Hello, World!

__Linking and running the Java Runtime__

    $ craftr -cb main:java.jlink
    $ build/debug/examples.java-mod/main-1.0.0-runtime/bin/greetings
    Hello, World!

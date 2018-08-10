### `craftr/examples/java-mod`

This example demonstrates how to produce a Java 9 module and creating a
standalone Java runtime with the `jlink` tool.

After the build of the `main:java.jlink` target finished, you will find a
`dist/main-1.0-0-runtime` directory that embeds the full Java binaries and
the example Java module. You can run the standalone Java application using:

    $ ./dist/main-1.0-runtime/bin/greetings
    Hello, World!

Targets:

* `main:java.jmod`
* `main:java.jlink`

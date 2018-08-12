### Example: `java-mod`

This example demonstrates how to produce a Java 9 module and creating a
standalone Java runtime with the `jlink` tool.

After the build of the `main:java.jlink` target finished, you will find a
`dist/main-1.0-0-runtime` directory that embeds the full Java binaries and
the example Java module. You can run the standalone Java application using:

```
$ craftr -cb --project examples/java-mod main:java.jlink
[examples.java-mod@main/java.jmod-com.greetings#1] SKIP
[examples.java-mod@main/java.jlink#1] Creating Java Runtime C:\Users\niklas\Repositories\craftr-build\craftr4\examples\java-mod\dist\main-1.0-0-runtime ...
  $ rm -rf 'C:\Users\niklas\Repositories\craftr-build\craftr4\examples\java-mod\dist\main-1.0-0-runtime'
  $ jlink --module-path 'C:\Users\niklas\Repositories\craftr-build\craftr4\build\debug\examples.java-mod\main\jmods' --add-modules com.greetings --output 'C:\Users\niklas\Repositories\craftr-build\craftr4\examples\java-mod\dist\main-1.0-0-runtime' --launcher greetings=com.greetings/com.greetings.Main --compress=2 --strip-debug --no-header-files --no-man-pages
$ ./dist/main-1.0-runtime/bin/greetings
Hello, World!
```

Targets:

* `main:java.jmod`
* `main:java.run`
* `main:java.jlink`

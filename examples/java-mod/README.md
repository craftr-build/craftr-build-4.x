## examples/java-mod

This example demonstrates how to produce a Java 9 module (`.jmod`) and
creating a standalone Java runtime with the `jlink` tool.

### Build & Run

**TODO**: Java does not seem to recognize `.jmod` files built by Craftr...

```
$ craftr -cf examples/java-mod/ -b main:java.run
note: writing "build\debug\build.ninja"
note: Ninja v1.8.2 (build\debug\ninja.exe)
[0/1] "C:\program files\python36\python.exe" c:\users\niklas\repo...inja\buildslave.py examples.java-mod@main:java.run^11342586680e 0 Error occurred during initialization of boot layer
java.lang.module.FindException: Module com.greetings not found

------------------------------------------------------------
fatal: "examples.java-mod@main:java.run" exited with code 1.
Command list:
> $ java -p build\debug\examples.java-mod\main\jmods -m com.greetings/com.greetings.Main
------------------------------------------------------------

FAILED: examples.java_mod_main_java.run
"C:\program files\python36\python.exe" c:\users\niklas\repositories\nodepy\nodepy\nodepy\main.py C:\Users\niklas\Repositories\craftr-build\craftr\craftr\lib\craftr\backends\ninja\buildslave.py examples.java-mod@main:java.run^11342586680e 0
ninja: build stopped: subcommand failed.
```

### Build Standalone Runtime

```
$ craftr -cf examples/java-mod/ -b main:java.jlink
[...]
$ build/debug/examples.java-mod/main-1.0.0-runtime/bin/greetings
Hello, World!
```

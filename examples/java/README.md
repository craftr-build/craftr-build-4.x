## examples/java

This example demonstrates how to build a Java application with dependencies
and bundling them into a single executable JAR. Note, in order to build and
run the bundle, use the `main:java.bundle` and `main:java.runBundle` targets
instead.

### Build & Run

```
$ craftr -cf examples/java/ -b main:java.run
[examples.java@lib] Resolving JARs...
  org.tensorflow:tensorflow:1.4.0 (default)
  | org.tensorflow:libtensorflow:1.4.0 (default)
  | org.tensorflow:libtensorflow_jni:1.4.0 (default)
[examples.java@main] Resolving JARs...
  org.tensorflow:tensorflow:1.4.0 (CACHED)
note: writing "build\debug\build.ninja"
note: Ninja v1.8.2 (build\debug\ninja.exe)
[5/8] "C:\program files\python36\python.exe" c:\users\niklas\repo...nds\ninja\buildslave.py examples.java@lib:java.jar^3dc58acb1b74 0 added manifest
adding: lib/(in = 0) (out= 0)(stored 0%)
adding: lib/Example.class(in = 2975) (out= 1454)(deflated 51%)
[7/8] "C:\program files\python36\python.exe" c:\users\niklas\repo...ds\ninja\buildslave.py examples.java@main:java.jar^d94a39092d41 0 added manifest
adding: Main.class(in = 336) (out= 242)(deflated 27%)
[7/8] "C:\program files\python36\python.exe" c:\users\niklas\repo...ds\ninja\buildslave.py examples.java@main:java.run^1acbb66f6698 0 2018-03-31 11:21:44.817375: I tensorflow/core/platform/cpu_feature_guard.cc:137] Your CPU supports instructions that this TensorFlow binary was not compiled to use: AVX AVX2
Hello from 1.4.0
```

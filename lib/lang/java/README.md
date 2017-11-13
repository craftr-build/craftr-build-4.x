# Java language module

Compile Java projects.

## Features

* Download dependencies from Maven Central (TODO: recursive dependency download)
* Combine JARs using OneJar or by merging them (vendors OneJar-boot 0.97)
* Apply ProGuard to your JARs (vendors ProGuard 5.3.3)

__Todolist__

* Support inclusion of resource files in JARs
* More options (warning flags, debug/release, linting, etc.)

## Options

* `java.onejar` (str)
* `java.javac` (str)
* `java.javac_jar` (str)
* `java.extra_arguments` (list of str)
* `java.dist_type` (str)
* `java.maven_repos` (dict of (str, str)) &ndash; A dictionary that maps
  name-strings to Maven repository URLs. The default repository with the name
  `default` points to the URL http://repo1.maven.org/maven2/ and can be 
  overwritten with a different URL or be disabled by setting it to `false`
  or an empty string.

## Functions

All functions inherit the standard parameters of targets:

* `name`
* `deps`
* `transitive_deps`
* `explicit`

### `java.library(**params)`

__Parameters__

* `jar_dir`
* `jar_name`
* `javac_jar`
* `main_class`
* `srcs`
* `src_roots`
* `class_dir`
* `javac`
* `extra_arguments`

### `java.binary(**params)`

__Parameters__

* `jar_dir`
* `jar_name`
* `javac_dir`
* `main_class`
* `dist_type`

### `java.prebuilt(**params)`

__Parameters__

* `binary_jar` (str)
* `binary_jars` (list of str)
* `artifact` (str)
* `artifacts` (list of str)

### `java.proguard(**params)`

__Parameters__

* `pro_file`
* `options`
* `cwd`
* `java`
* `outjars`

### `java.run(target, *argv, **params)`

__Parmeters__

* `target` (str or Target) &ndash; A target reference or a Target object that
  was created with `java.binary()`
* `*argv` (str) &ndash; Additional arguments for the binary.
* `name` (str) &ndash; The target name. Defaults to the name of the specified
  *target* with an appended `_run`.
* `java` (str) &ndash; Name of the `java` executable to run. Defaults to the
  `java.java` option.
* `jvm_args` (str) &ndash; Additional arguments passed before the `-jar <JAR>`
  parameter.

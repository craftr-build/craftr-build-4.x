# Java language module

Compile Java projects.

## Options

* `java.onejar` (str)
* `java.javac` (str)
* `java.javac_jar` (str)
* `java.extra_arguments` (list of str)
* `java.dist_type` (str)

## Functions

### `java.library()`

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

### `java.binary()`

__Parameters__

* `jar_dir`
* `jar_name`
* `javac_dir`
* `main_class`
* `dist_type`

### `java.prebuilt()`

__Parameters__

* `binary_jar`

## Todo

* Support inclusion of resource files in JARs
* More options (warning flags, debug/release, linting, 
  provided dependencies, etc.)
* Ability to download dependencies from mavencentral or other repositories

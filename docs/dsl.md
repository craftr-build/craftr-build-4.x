# The Craftr build language

## Introduction

Craftr uses its own language to allow you to define build targets. The goal
of this language is to have a flexible and expressive and yet powerful syntax
for describing build information.

The DSL allows you to write inline-Python code, and every property that you
assign on the module, target or dependency level is evaluated as a full Python
expression. The Python used by Craftr has some additional features regarding
built-in variables and syntax.

Importing other build scripts or Python scripts can be done using the [Node.py]
module import syntax, for example:

```python
project "myproject"
import "craftr/lang/java"
import utils from "./utils"
```

Importing other Craftr build scripts always require the `.craftr` suffix. Once
another Craftr module is imported, it is part of the build process.

The standard library provides a bunch of modules that implement build support
for various programming languages. Once such a module is imported, properties
that are supported by that module can be set on modules and dependencies, but
most of the time on targets.

```python
project "myproject"
import "craftr/lang/java"
target "main":
  java.srcs = glob('src/**/*.java')
```

## Syntax Documentation

A build script consists of statements and blocks, and most blocks have their
own inner grammar. Not all blocks can be nested inside each other.

### Example

```python
project "myproject" v1.6.4

# A block of TOML formatted configuration values. These are applied only
# when your build script is the builds' entry point.
configure:
  [myproject]
  option1 = 42

# A block of options expected by the module. Options without default value
# must be set, otherwise there will be an error. The options are made available
# as an object called "objects" in the global namespace of the module.
options:
  int option1
  str option2 = "Hello, World"
  bool option3 = False

eval print('This is a single line of Python code! option2:', options.option2)

# A block of Node.py-processed Python code.
eval:
  print('This is a block of Python code!')
  print('The options you chose are:', options.option1, options.option2, options.option3)
  print('You are on', OSNAME)
  includes = ['./include']

# An import-line, the same can be put inside an eval: block.
# Allows you to import other Craftr build modules, Python or Node.py modules.
import "craftr/lang/cxx"

# Declare a pool where targets can be assigned to.
pool "myPool" 4

# Declare a public target. Exported targets are publicly visible and
# automatically depended on when declaring a dependency to the module in
# another target.
public target "lib":

  # Declare an exported dependency to the module "libcurl.craftr".
  # Exported dependencies are inherited transitively by other targets.
  export requires "libcurl":
    cxx.link = True  # That's the default

  # Assign the target to a pool. Note that this may not always be respected
  # by the target build handler.
  this.pool = "myPool"

  # Set property values -- note that these properties can only be set because
  # the "cxx.craftr" module was imported previously.
  cxx.type = 'library'
  cxx.srcs = glob(['./src/*.cpp', './src/' + OSNAME + '/*.cpp'],
    excludes = ['./src/main.cpp'])

  # Exported properties CAN be inherited transitively by targets that
  # depend on this target. Whether the information is considered is up
  # to the target handler implementation.
  export cxx.includePaths = includes
  export:
    cxx.includePaths = includes

# Declare a non-public target. Can still be explicity depended on using
# `requires "myproject@main"`.
target "main":
  requires "@lib"
  cxx.srcs = ['./src/main.cpp']
```

## Conditional Blocks

The following blocks can be made condition by appending a Python `if ...`
statement

* export
* eval
* target
* requires

Example:

```python
project "sfml"
import "craftr/lang/cxx"
import {pkg_config} from "craftr/tools/pkg-config"
eval if False:
  print("This gets never executed")
target "sfml" if OS.id != 'win32':
  requires "somelib" if some_condition:
    prop.name = "here"
  requires "anotherlib" if another_condition
  eval pkg_config(target, 'SFML-all')
target "sfml" if OS.id == 'win32':
  cxx.includes = ...
  # etc etc
```

## Target Properties

Target blocks have a set of default properties.

| Property        | Type | Description |
| --------------- | ---- | ----------- |
| `this.pool`     | str  | The name of a job pool to execute the target in. Note that some target handlers may provide their own properties to override the pool for certain parts of the build. |
| `this.syncio`   | bool | Synchronize the standard input/output of commands executed by the target with the console. This does not pair with the `pool` option. |
| `this.explicit` | bool | Do not build this target unless it is required by another target or it is explicitly specified on the command-line. |
| `this.directory`| str  | The directory to consider relative paths relative to. A relative path will still be considered relative to the original path. |


## Built-in variables

These variables are available inside Craftr build scripts -- not in normal
Node.py/Python scripts.

| Name | Type | Description |
| - | - | - |
| `path` | module | The `nr.path` module -- available for convenience. |
| `options` | `ModuleOptions` | A `ModuleOptions` object. This will be filled with the actual option values after the first `options:` block. You can use this in an `eval:` block before the first `options:` block to initialize default values. |
| `OS` | `OsInfo` | An `OsInfo` object that contains the name, id, type and arch of the current operating system. Possible names are `windows`, `macos` and `linux`. Possible IDs are `win32`, `darwin` and `linux`. Possible types are `nt` and `posix`. Note that on Windows Cygwin, the type will also be `posix`.  Possible architectures are `x86_64` and `x86`. |
| `BUILD` | `BuildInfo` | A `BuildInfo` object that tells you whether this is a release or debug build. Members of this object are `mode`, `debug` and `release`. |
| `error(message)` | function | Raise an error (`craftr.dsl.ExplicitRunError`) with the specified message. |
| `fmt(format)` | function | Expects a Python `str.format()` string that will be substituted in the context of the current global and local variables. |
| `glob(patterns, excludes=[], parent=None)` | function | Match glob patterns relative to `parent`. If `parent` is omitted, defaults to directory of the build script or the target if explicitly set with `this.directory`. |

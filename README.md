<img align="right" src=".assets/craftr-logo.png">

# Craftr

&mdash; A modular and language-independent build system. *Version 3.0.0-dev*

<a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
<a href="https://travis-ci.org/craftr-build/craftr"><img src="https://travis-ci.org/craftr-build/craftr.svg?branch=craftr-3.x"></a>
<a href="https://ci.appveyor.com/project/NiklasRosenstein/craftr"><img src="https://ci.appveyor.com/api/projects/status/6v01441cdq0s7mik?svg=true"></a>

## Features

  [Node.py Package Manager]: https://github.com/nodepy/nodepy-pm

* Craftr is installed on a **per-project** basis
* Build scripts are written in Python (with some sugar)
* Native support for a variety of languages
* Builds 100% outside the project worktree
* Install libraries or additional language support extensions using the
  [Node.py Package Manager]

__Todolist__

* Language modules for Cython and Vala
* The default build backend sometimes runs into a deadlock when interrupting
  the build process with CTRL+C
* Determine additional file dependencies for C/C++ build targets using MSVC
  `/showIncludes` and GCC/Clang respective options

## Installation

__Preparation__

* Install Python3.6+ ([download page](https://www.python.org/downloads/release/python-363/))
* Install the [Node.py Runtime](https://nodepy.org)
* Install the [Node.py Package Manager]

```
$ pip3.6 install --user git+https://github.com/nodepy/nodepy.git@develop
$ nodepy https://nodepy.org/install-pm -g master
```

__Installing Craftr__


```
$ nodepy-pm install git+https://github.com/craftr-build/craftr.git@craftr-3.x
```

This will install Craftr into the current directory. It is recommended that
you update the `PATH` variable (eg. in your `.profile` or just in your current
session) to access the `craftr` command-line tool.

```
$ export PATH="$(nodepy-pm bin):$PATH"
$ craftr --version
```

You should also consider creating a `nodepy.json` manifest which allows you
to track your dependencies (eg. the exact Craftr version/git ref). To always
install the newest Craftr version has the potential to break your build, thus
you should always work with the same version, or explicitly upgrade to a newer
version, ensuring that the build still works or otherwise make adjustments.

Example:

```json
{
  "name": "myproject",
  "version": "1.0.0",
  "publish": false,
  "cfg(dev).dependencies": {
    "craftr": "git+https://github.com/craftr-build/craftr.git@craftr-3.x"
  }
}
```

## Getting started

Check out one of the projects in the `examples/` directory. To get you hooked,
here's some example build scripts for Java, C# and C/C++. To run any of the
examples, simply use

```
$ craftr --verbose :main_run
```

### Java

```python
import {glob} from 'craftr'
import java from 'craftr/lang/java'

java.prebuilt(name = 'libs', artifacts = [
  'com.google.guava:guava:23.4-jre',
  'com.tensorflow:tensorflow:1.4.0'
])

java.binary(
  name = 'main',
  deps = [':libs'],
  srcs = glob('src/**/*.java'),
  main_class = 'Main',
  dist_type = 'merge'  # Works better with TensorFlow than 'onejar'
)

java.run(':main')
```

### C#

```python
import {glob} from 'craftr'
import csharp from 'craftr/lang/csharp'

csharp.prebuilt(name = 'libs', packages = [
  'Newtonsoft.Json:10.0.3'
]) 

csharp.build(
  name = 'main',
  deps = [':libs'],
  srcs = glob('src/**/*.cs'),
  type = 'exe',
  merge_assemblies = True
)

csharp.run(':main')
```

### C/C++

```python
import {gentarget, glob, t} from 'craftr'
import cxx from 'craftr/lang/cxx'

cxx.build(
  name = 'lib',
  type = 'library',
  srcs = glob('src/**/*.c'),
  libname = '$(lib)myproject$(ext 1.3)',
)

cxx.build(
  name = 'main',
  type = 'binary',
  srcs = 'main.c'
)

cxx.run(':main')
```

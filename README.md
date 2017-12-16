<img align="right" src=".assets/craftr-logo.png">

## The Craftr build system

<a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-yellow.svg"></a>
<a href="https://travis-ci.org/craftr-build/craftr"><img src="https://travis-ci.org/craftr-build/craftr.svg?branch=craftr-3.x"></a>
<a href="https://ci.appveyor.com/project/NiklasRosenstein/craftr"><img src="https://ci.appveyor.com/api/projects/status/6v01441cdq0s7mik?svg=true"></a>
<img src="https://img.shields.io/badge/version-3.0.0--dev-blue.svg"/>

  [Ninja]: https://github.com/ninja-build/ninja.git
  [Node.py]: https://github.com/nodepy/nodepy
  [nodepy-pm]: https://github.com/nodepy/nodepy-pm

Craftr is a modular meta build system that primarily targets [Ninja] as the
build backend. Craftr is language-independent and can be extended to represent
any build process. It is also not limited to a single language per project.
Craftr comes pre-packaged with support for a number of languages that currently
include C/C++, C# and Java.

Build scripts are written in Python (with sugar inherited from the [Node.py]
runtime) and thus allow you to express very complex build requirements very
easily. Due to its modular nature, writing and using Craftr extensions (be it
helpers for your projects or support for a new programming language) can be
easily implemented and installed using [Node.py's Package manager][nodepy-pm].

### Installation

Make sure you have at least [Python 3.6](https://www.python.org/downloads/release/python-363/)
installed on your system, then follow these steps:

    # Install Node.py (https://nodepy.org)
    pip3.6 install --user git+https://github.com/nodepy/nodepy.git@develop

    # Install the Node.py Package Manager
    nodepy https://nodepy.org/install-pm -g master

    # Install Craftr into your current project directory
    cd ~/repos/myproject
    nodepy-pm install git+https://github.com/craftr-build/craftr.git@craftr-3.x
    export PATH=.nodepy/bin:${PATH}

### Quickstart

    craftr --quickstart {java,csharp,cxx}

This will copy one of the example projects into your current directory.

### Usage

Craftr uses a three-step build-process: `--configure`, `--prepare-build` and
`--build`. Fear not that you must use three separate commands to get going
with a build, however, as all steps can run in a single command. The `--build`
step also implies `--prepare-build`, so compiling a new project usually comes
down to just `craftr --configure --build`. If your project hasn't changed to
the extend that the build graph needs to be updated, subsequent calls use
just the `--build` step to avoid the (long, for big projects) reconfiguration
step.

Since Craftr primarily targets the [Ninja] build system as its backend, it is
useful to have a version of Ninja installed on your system (min 1.7.1). If you
don't have (a matching version of) Ninja installed however, Craftr will
automatically download a version for you into the build directory.

Build scripts are called `BUILD.cr.py`. Configuration values can be defined
in the `BUILD.cr.toml` file or with the `--options` command-line argument.
Every script usually wants to import the `craftr` main namespace initially,
then a module that implements compiling projects for the language you use.

Example for Java:

```python
import craftr from 'craftr'
import java from 'craftr/lang/java'

java.prebuilt(
  name = 'libs',
  artifacts = [
    'org.tensorflow:tensorflow:1.4.0'
  ]
)

java.binary(
  name = 'main',
  deps = [':libs'],
  srcs = craftr.glob('src/**.java'),
  main_class = 'Main'
)

java.run(':main')
```

The configure and build this project, and execute the compiled JAR archive:

    $ craftr --configure --build :main_run

---

<p align="center">Copyright &copy; Niklas Rosenstein 2015, 2016, 2017</p>

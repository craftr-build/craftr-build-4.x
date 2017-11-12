<img align="left" src=".assets/craftr-logo.png">
<h1 align="center">Craftr &ndash; Build Tool</h1>
<p align="center">
  A modular language-independent build system.<br/>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <a href="https://travis-ci.org/craftr-build/craftr"><img src="https://travis-ci.org/craftr-build/craftr.svg?branch=craftr-3.x"></a>
  <a href="https://ci.appveyor.com/project/NiklasRosenstein/craftr"><img src="https://ci.appveyor.com/api/projects/status/6v01441cdq0s7mik?svg=true"></a>
</p>

*Version 3.0.0-dev*

## Features

* Installed on a per-project basis, don't break builds due to a mismatching
  build-system version
* Completely modular structure, allowing you to write your own extensions
  for other languages or use other people's extensions
* Native support for a variety of languages (currently C# and Java)

__Todolist__

* Language modules for C, C++, Cython and Vala
* The default build backend sometimes runs into a deadlock when interrupting
  the build process with CTRL+C
* Trigger rebuild if the input variables (eg. system command that is being
  executed) changed since the last time the action was executed

## Installation

First, you need to install Node.py and its package manager:

    $ pip3.6 install --user git+https://github.com/nodepy/nodepy.git@develop
    $ nodepy https://nodepy.org/install-pm -g master

Craftr requires **Python 3.6** or higher. You install Craftr locally for your
project using the Node.py package manager:

    $ nodepy-pm install git+https://github.com/craftr-build/craftr.git@craftr-3.x
    $ export PATH="$(nodepy-pm bin):$PATH"
    $ craftr --version

Consider creating a `nodepy.json` package manifest in which you can track
Craftr and other (build-) dependencies for your project.

```json
{
  "name": "myproject",
  "version": "1.0.0",
  "cfg(dev).dependencies": {
    "craftr": "git+https://github.com/craftr-build/craftr.git@craftr-3.x"
  }
}
```

## Getting started

Check out one of the projects in the `examples/` directory. To get you hooked,
here's the build-script of the example Java project:

```python
import craftr from 'craftr'
import java from 'craftr/lang/java'

# Downloads Guava 23.4 from Maven Central.
java.prebuilt(name = 'guava', artifact = 'com.google.guava:guava:23.4-jre')

java.binary(
  name = 'main',
  deps = [':guava'],
  srcs = craftr.glob('src/**.java'),
  main_class = 'Main'
)

java.run(':main')
```

Build & run:

    $ craftr -bbuild --verbose :main_run

<p align="right">Current Version: v4.0.0.dev0</p>

# The Craftr build system

Craftr is a Python based meta build system with native support for C, C++,
C#, Java and Cython projects. It can be tailored to satisfy all needs of
modern build requirements.

## Features

[Node.py]: https://github.com/nodepy/nodepy

* Python-based build scripts <sup>1</sup>
* Modular, reusable build definitions
* Native support for a bunch of common languages

<sup>1) Build scripts are loaded through [Node.py] and and have access to an
  extended set of global variables provided by the `craftr.api` module.</sup>

## How does it work?

Build scripts in Craftr always have access to the members exported by the
`craftr.api` module. Every build script begins with a call to the `project()`
function. The Craftr API is implements as a "state machine" where subsequent
calls often depend on previous ones. As an example, the `target()` functions
creates a new target and binds it for future calls to `properties()` and
`operator()`.

The Craftr standard library provides functions that declare target properties
and functions to convert these properties into build operators. Such modules
must be loaded with `require()` before the properties can be set. Then after
the target information is complete, the module usually provides a `build()`
method that takes these parameters and turns it into concrete elements in the
build graph.

```python
# build.craftr
project('myproject', '1.0-0')
cxx = require('craftr/lang/cxx')
target('main')
properties({
  'cxx.srcs': glob('src/*.c'),
  'cxx.type': 'executable'
})
cxx.build()
```

## How to install?

Craftr requires Python 3.6 or newer (preferrably CPython) and can be installed
like any other Python modules.

    $ pip install craftr-build

To install the latest version from the Craftr GitHub repository use:

    $ pip install git+https://github.com/craftr-build/craftr.git -b develop

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>

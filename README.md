<p align="right">Current Version: v4.0.0.dev1</p>

# The Craftr build system

Craftr is a Python based meta build system with native support for C, C++,
C#, Java and Cython projects. It can be tailored to satisfy all build
requirements for modern applications.

## Features

[Node.py]: https://github.com/nodepy/nodepy
[Ninja]: https://ninja-build.org/

* Python-based build scripts <sup>1</sup>
* Modular, reusable build definitions
* Uses [Ninja] as lightning-fast build backend
* Native support for a bunch of common languages
  * C, C++
    * Compilers: MSVC, GCC, Clang
    * Windows: Automatic detection of an installed MSVC or MinGW/MSYS2 toolchain
  * Java
    * Support for Maven Repository dependencies
    * JAR bundling
    * Java Modules
    * jlink standalone runtimes
  * C#
    * Compilers: MSVC, Mono
    * NuGet Dependencies
    * ILMerge/ILRepack
  * Cython
  * Haskell
  * OCaml

<sup>1) Build scripts are loaded through [Node.py] and and have access to an
  extended set of global variables provided by the `craftr.api` module.</sup>

## What's next?

* Support passing additional arguments to a build operator (useful for
  operators that run a build product, eg `cxx.run`)
* Enhancements to the standard library (especiall C/C++)
* Reduce build graph JSON representation: Write the same `environ`
  dictionary only once and reference from `Operator` and `BuildSet`
  JSON representation.

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
cxx = require('cxx')
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

## Tips & Tricks

### How to show Python warnings?

The Craftr API makes some usage of the Python `warnings` module. If you want
warnings to be displayed, you can add `PYTHONWARNINGS=once` to the environment,
or use the `--pywarn[=once]` command-line flag which is usually preferred
because you won't see the warnings caused by your Python standard library.


## Synopsis

```
usage: craftr [-h] [--variant [=debug]] [--project PATH] [--module-path PATH] [--config-file PATH]
              [-O K=V] [--build-root PATH=[build]] [--backend MODULE] [-c] [-b] [--clean] [-v] [-r]
              [--tool ...] [--dump-graphviz [FILE]] [--dump-svg [FILE]] [--notify]
              [[TARGET [...]] [[TARGET [...]] ...]]

optional arguments:
  -h, --help                 show this help message and exit

Configuration:
  --variant [=debug]         Choose the build variant (debug|release).
  --project PATH             The Craftr project file or directory to load.
  --module-path PATH         Additional module search paths.
  --config-file PATH         Load the specified configuration file. Defaults to "build.craftr.toml"
                             or "build.craftr.json" in the project directory if the file exists.
  -O K=V, --option K=V       Override an option value.
  --build-root PATH=[build]  The build root directory. When used, this option must be specified with
                             every invokation of Craftr, even after the config step.
  --backend MODULE           Override the build backend. Can also be specified with the
                             build:backend option. Defaults to "net.craftr.backend.ninja".

Configure, build and clean:
  [TARGET [...]]             Allows you to explicitly specify the targets that should be built
                             and/or cleaned with the --build and --clean steps. A target specifier
                             is of the form "[scope@]target[:operator]. If the scope is omitted, it
                             falls back to the project's scope. If the operator is not specified,
                             all non-explicit operators of the target are used. Logical children of
                             one target are automatically included when their parent target is
                             matched.
  -c, --config               Configure step. Run the project build script and serialize the build
                             information. This needs to be re-run when the build backend is changed.
  -b, --build                Build step. This must be used after or together with --config.
  --clean                    Clean step.
  -v, --verbose              Enable verbose output in the --build and/or --clean steps.
  -r, --recursive            Clean build sets recursively.

Tools and debugging:
  --tool ...                 Invoke a Craftr tool.
  --dump-graphviz [FILE]     Dump a GraphViz representation of the build graph to stdout or the
                             specified FILE.
  --dump-svg [FILE]          Render an SVG file of the build graph's GraphViz representation to
                             stdout or the specified FILE. Override the layout engine with the
                             DOTENGINE environment variable (defaults to "dot").
  --notify                   Send a notification when the build completed. Requires the ntfy module
                             to be installed.
```

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>

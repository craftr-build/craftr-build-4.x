<p align="right">Current Version: v4.0.0.dev2</p>

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

Craftr build scripts are executed with the [Node.py] runtime, allowing them
to use the `import <...> from 'module'` syntax to import from other Craftr
build scripts/modules.

While the Craftr API can also be acceseed via the `craftr.api` module, it is
often more convenient to import from the `'craftr'` module instead. All API
functions must be imported explicitly, either one by one, using the starred
import or into a module object.

```python
import {project, target, properties} from 'craftr'  # 1)
import * from 'craftr'                              # 2)
import craftr from 'craftr'                         # 3)
```

The Craftr build script API is implemented as "state machine" where the
last declared target is "bound" for future operations like `properties()`
or `operator()`.

Build modules need to be imported before properties belonging to that module
are set on a target with the `properties()` function. After a target has been
set up, that modules `build()` method must be called.

```python
# build.craftr
import {project, target, properties, glob, options} from 'craftr'
import cxx from 'cxx'

project('myproject', '1.0-0')

target('main')
properties({
  'cxx.srcs': glob('src/*.c'),
  'cxx.type': 'executable'
})
cxx.build()
```

There are some fundamental built-ins available to Craftr modules that
do not need to be imported:

<table>
<tr><th>Name</th><th>Description</th></tr>
<tr>
  <td><code>module</code></td>
  <td>The <code>CraftrModule</code> object.</td>
</tr>
<tr>
  <td><code>module.options</code></td>
  <td>

  This is actually a member of the `module` object but it is important to be
  described separately. This object allows you to conveniently specify typed
  build options that can be used later on in your build script.
  *Important:* You must call `project()` before declaring options, otherwise
  your module has no scope name assigned.

  ```python
  project('com.me.myapp', '1.0-0')
  options = module.options
  options.add('version', str, '7.51.0')
  ```

  The `version` option can now be set with `-Omyapp:version=8.21.2` or to be
  more explicit with `-Ocom.me.myapp:version=8.21.2`.

  </td>
</tr>
<tr>
  <td><code>require</code></td>
  <td>

  This is the function/object that is used to load other Craftr/Node.py
  modules. Using the `import <...> from 'module'` syntax is automatically
  converted to a pure Python statement that uses the `require()` function.

  You can use it to load a module from the Craftr standard library or load
  other helper modules into your build script.

  ```python
  cxx = require('net.craftr.lang.cxx')
  utils = require('./utils')
  import {do_stuff} from './utils'
  ```

  </td>
</tr>
</table>

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

# Craftr 2

[![PyPI Version](https://img.shields.io/pypi/v/craftr-build.svg)](https://pypi.python.org/pypi/craftr-build)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/530/badge)](https://bestpractices.coreinfrastructure.org/projects/530)

Craftr is a meta build system based on [Python 3] scripts which produces
[Ninja] build manifests. It enforces the use of modular build definitions
that can be re-used easily and ships with a standard library supporting
various programming languages and common libraries.

- [Documentation]
- [Getting Started]
- [Craftr 2.x Wiki][Wiki]

__Features__

- [x] Aims to be cross-platform compatible (regularly tested on Windows, Mac OS and Linux)
- [x] Build definitions divided into versioned modules
- [x] Embedd actual Python functions into the build process (keyword Tasks)
- [x] Dependency-lock files for fully reproducible builds
- [ ] Package manager (hosted on [Craftr.net])

__Basic Usage__

    $ craftr version                            # Print Craftr version and exit
    $ craftr export                             # Generate Ninja manifest
    $ craftr build [target [target [...]]]      # Build all or the specified target(s)
    $ craftr clean [-r] [target [target [...]]] # Clean all or the specified target(s)
    $ craftr startpackage <name> [directory]    # Start a new Craftr project (manifest, Craftrfile)
    $ craftr lock                               # Generate a .dependency-lock file (after craftr export)

__C++ Example__

```python
cxx = load('craftr.lang.cxx')
program = cxx.executable(
  inputs = cxx.compile_cpp(sources = glob('src/**/*.cpp')),
  output = 'main'
)
```

__Java Example__

```python
java = load('craftr.lang.java')
jar = java.jar(
  inputs = java.compile(src_dir = local('src')),
  output = 'myapp',
  entry_point = 'Main'
)
```

__C# Example__

```python
cs = load('craftr.lang.csharp')
app = cs.compile(
  sources = glob('src/**/*.cs'),
  output = 'Main',
  target = 'exe'
)
```

__Cython Exmple__

```python
cython = load('craftr.lang.cython')
primes = cython.project(
  sources = [local('Primes.pyx')],
  main = local('Main.pyx')
)
run = runtarget(primes.main)
```

[Ninja]: https://github.com/ninja-build/ninja
[Python 3]: https://www.python.org/
[Documentation]: https://github.com/craftr-build/craftr/tree/master/doc
[Getting Started]: https://github.com/craftr-build/craftr/tree/master/doc/getting-started.md
[Wiki]: https://github.com/craftr-build/craftr/wiki
[Craftr.net]: https://craftr.net

## How to Contribute

Please [create an Issue](https://github.com/craftr-build/craftr/issues/new) if
you have any questions, problems or feature requests.

## Installation

Make sure you specify the specific version you want to install since there is
no untagged version of Craftr 2.x available on PyPI yet and otherwise Pip will
install Craftr 1.x (which is quite different). To get the newest stable version
of Craftr 2, use

    $ pip install craftr-build==2.0.0.dev5

To get the cutting edge development version, I suggest installing Craftr
from the Git repository into a virtualenv.

    $ virtualenv -p python3 env && source env/bin/activate
    $ git clone https://github.com/craftr-build/craftr.git -b development
    $ cd craftr
    $ pip install -e .

## Requirements

- [Ninja] 1.7.1 or newer
- [CPython][Python 3] 3.4 or 3.5

__Python Dependencies (automatically installed)__

- [colorama](https://pypi.python.org/pypi/colorama) (optional, Windows)
- [glob2](https://pypi.python.org/pypi/glob2)
- [jsonschema](https://pypi.python.org/pypi/jsonschema)
- [ninja_syntax](https://pypi.python.org/pypi/ninja_syntax)
- [nr](https://pypi.python.org/pypi/nr)
- [py-require](https://pypi.python.org/pypi/py-require)
- [termcolor](https://pypi.python.org/pypi/termcolor) (optional)
- [werkzeug](https://pypi.python.org/pypi/werkzeug)

## License

    The Craftr build system
    Copyright (C) 2016  Niklas Rosenstein

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

For more information, see the `LICENSE.txt` file.

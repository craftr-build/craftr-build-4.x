# Craftr 2.x
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/530/badge)](https://bestpractices.coreinfrastructure.org/projects/530)

> Note: This is the development version of the new version of Craftr. It is
> different from the initial Craftr version in many ways and can not be used
> interchangibly. The latest version of Craftr 1 can be found under tag
> [v1.1.4-unreleased](https://github.com/craftr-build/craftr/tree/v1.1.4-unreleased).

Craftr is a meta build system based on [Python 3] scripts which produces
[Ninja] build manifests. It enforces the use of modular build definitions
that can be re-used easily. Craftr provides a standard library to support
various programming languages and common libraries out of the box:

- C/C++
- Cython
- C#
- Java
- Vala

Check out the [Documentation] and the [Getting Started] page.

  [Ninja]: https://github.com/ninja-build/ninja
  [Python 3]: https://www.python.org/
  [Documentation]: doc
  [Getting Started]: doc/getting-started.md

## Features

- [x] Moduler build scripts (Craftr packages) with dependency management
- [x] Loaders: if required, automatically download and build libraries from source!
- [ ] Package manager (hosted on [Craftr.net])
- [ ] Embed actual Python functions into the build graph
- [ ] Dependency-version lockfiles


  [Craftr.net]: https://craftr.net

## Installation

Craftr 2.x is currently not on PyPI so you have to install it from the Git
repository. Note that the most recent version of Craftr might also require
an unreleased version of the `nr` module, thus it is recommended to install
it from the Git repository as well.

    $ virtualenv -p python3 env && source env/bin/activate
    $ git clone https://github.com/NiklasRosenstein/py-nr.git
    $ pip install -e py-nr
    $ git clone https://github.com/craftr-build/craftr.git
    $ pip install -e craftr
    $ craftr version
    2.0.0-dev

## Requirements

- [Ninja] 1.7.1 or newer
- [Python][Python 3] 3.4, 3.5

### Python

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

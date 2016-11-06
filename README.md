# craftr

Craftr is a meta build system that produces [Ninja] build manifests from
simple [Python 3] scripts. It provides a high level of abstraction but gives
you 100% control over the build process.

This repository contains the in-development version of Craftr 2. The current
stable version of Craftr 1 can be found [here](https://github.com/craftr-build/craftr).

  [Ninja]: https://github.com/ninja-build/ninja
  [Python 3]: https://www.python.org/

## Requirements

- [colorama](https://pypi.python.org/pypi/colorama) (optional, Windows)
- [glob2](https://pypi.python.org/pypi/glob2)
- [jsonschema](https://pypi.python.org/pypi/jsonschema)
- [ninja_syntax](https://pypi.python.org/pypi/ninja_syntax)
- [nr](https://pypi.python.org/pypi/nr)
- [py-require](https://pypi.python.org/pypi/py-require)
- [termcolor](https://pypi.python.org/pypi/termcolor) (optional)

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
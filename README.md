# craftr

Craftr is a meta build system based on [Python 3] scripts which produces
[Ninja] build manifests. It enforces the use of modular and build definitions
that can be re-used easily. Craftr provides a standard library to support
various programming languages and common libraries out of the box:

- C/C++
- Cython
- C#
- Java

Below you can find an example to compile a simple C++ program to get a taste
of what Craftr build definitions look like. Note that every module requires a
`manifest.json` together with a `Craftrfile` to make a *package*.

__manifest.json__

```json
{
  "name": "myapp",
  "version": "1.0.0",
  "dependencies": {
    "lang.cxx": "*",
    "lib.cxx.curlpp": "*"
  }
}
```

__Craftrfile__

```python
load_module('lang.cxx.*')
load_module('lang.cxx.curlpp.*')

program = cxx_binary(
  inputs = cpp_compile(
    sources = glob(['src/*.cpp']),
    frameworks = [cURLpp]
  ),
  output = 'main'
)
```

This project can now be built using the `craftr build` command. Depending on
the availability, the `cURLpp` library will be compiled from source or the
flags will be retrieved with `pkg-config` (TODO).

Note that you can start a new project easily with the `craftr startproject`
command.

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
# Craftr 2.x

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

Below you can find an example to compile a simple C++ program to get a taste
of what Craftr looks like. Note that every module requires a `manifest.json`
together with a `Craftrfile` to make a *package*.

> __Note__: You can start a new package easily with the `craftr startpackage`
> command.

__manifest.json__

```json
{
  "name": "examples.c",
  "version": "1.0.0",
  "dependencies": {
    "craftr.lang.cxx": "*"
  },
  "options": {
    "debug": {
      "type": "bool"
    },
    "outbin": {
      "type": "string",
      "default": "my_app"
    }
  }
}
```

__Craftrfile__

```python
# examples.c

from os import environ
load_module('craftr.lang.cxx.*')

program = cxx_binary(
  inputs = c_compile(
    sources = glob(['src/*.c'])
  ),
  output = options.outbin
)

run = runtarget(program, environ.get('USERNAME', 'John'), "sunny")

```

__C Sources__
```c
$ cat src/hello.c

#include <stdio.h>

void say_hello(char const* name, char const* weather) {
  printf("Hello, %s. You are facing a %s day\n", name, weather);
}

$ cat src/main.c

extern void say_hello(char const* name, char const* weather);

int main(int argc, char** argv) {
  if (argc != 3) {
    printf("error: usage: %s name weather\n");
    return 0;
  }
  say_hello(argv[1], argv[2]);
  return 0;
}
```
To export, build and run the project, use

    $ craftr export
    $ craftr build
    $ craftr build run
    Hello, John. You are facing a sunny day

Note that the `build` command accepts target names as additional arguments.
Since `run` is just another target, that's how we can invoke the test command
that we created with `runtarget()`.

Due to the way Craftr organizes the build tree, the output file will be
located in `build/examples.c-1.0.0/my_app`. If you want to define an exact path
for the output file, use an absolute path. For example `local()` gives you
an absolute path assuming the path you give it is relative to your project
directory.

```python
# ...
  output = local(options.outbin)
# ...
```

Options can either be specified on the command-line or in configuration files.
By default, `~/.craftrconfig` and `./.craftrconfig` files are loaded if they
exist. The `-c <filename>` option can be used to pass one or more configuration
filenames that will be loaded instead of `./.craftrconfig` (note that the file
in the user home directory is still loaded).

```ini
# .craftrconfig
[__global__]
  debug = true
[examples.c]
  outbin = my_app
[include "config/another.config"]
```

You can also find this example in [`examples/examples.c`](examples/examples.c).

Check out the [Documentation].

  [Ninja]: https://github.com/ninja-build/ninja
  [Python 3]: https://www.python.org/
  [Documentation]: doc

## Features

- [x] Moduler build scripts (Craftr packages) with dependency management
- [x] Loaders: if required, automatically download and build libraries from source!
- [ ] Package manager (hosted on [Craftr.net])
- [ ] Dependency-version lockfiles
- [ ] RTS and Tasks (as Craftr 1 used to have)


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

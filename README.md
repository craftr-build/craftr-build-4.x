# Craftr

[![PyPI Downloads](http://img.shields.io/pypi/dm/craftr-build.svg)](https://pypi.python.org/pypi/craftr-build)
[![PyPI Version](https://img.shields.io/pypi/v/craftr-build.svg)](https://pypi.python.org/pypi/craftr-build)
[![Travis CI](https://travis-ci.org/craftr-build/craftr.svg)](https://travis-ci.org/craftr-build/craftr)

Craftr is the build system of the future based on [Ninja][] and [Python][].

* [x] Modular build scripts
* [x] Cross-platform support
* [x] Low- and high-level interfaces for specifying build dependencies and commands
* [x] Good performance compared to traditional build systems like CMake and Make or Meson
* [x] LDL: Language-domain-less, Craftr is an omnipotent build system
* [x] Extensive STL with high-level interfaces to common compiler toolsets like
      MSVC, Clang, GCC, Java, Protobuf, Yacc, Cython, Flex, NVCC
* [x] **Consequent** out-of-tree builds

### Getting Started

Craftr uses `Craftfile.py` or `craftr.ext.<module_name>.py` files as build scripts.
`Craftfile.py` files require the `# craftr_module(...)` line and are automatically
detected by Craftr as the project's main script.

```python
# craftr_module(my_project)

from craftr import path                   # similar to os.path with a lot of additional features
from craftr.ext.platform import cxx, ld   # import the C++ compiler and Linker for the current platform

# Create object files for each .cpp file in the src/ directory.
obj = cxx.compile(
  sources = path.glob('src/*.cpp')
)

# Link all object files into an executable called "main".
program = ld.link(
  output = 'main',
  inputs = obj
)
```

Run Craftr from the command-line:

    niklas ~/Desktop/test $ craftr -eb -N -v
    craftr: [INFO ]: Changed directory to "build"
    [1/3] clang++ -x c++ -c /Users/niklas/Desktop/test/src/main.cpp -o /Users/niklas/Desktop/test/build/my_project/obj/main.o -stdlib=libc++ -Wall -O0 -MD -MP -MF /Users/niklas/Desktop/test/build/my_project/obj/main.o.d
    [2/3] clang++ -x c++ -c /Users/niklas/Desktop/test/src/foo.cpp -o /Users/niklas/Desktop/test/build/my_project/obj/foo.o -stdlib=libc++ -Wall -O0 -MD -MP -MF /Users/niklas/Desktop/test/build/my_project/obj/foo.o.d
    [3/3] clang /Users/niklas/Desktop/test/build/my_project/obj/foo.o /Users/niklas/Desktop/test/build/my_project/obj/main.o -lc++ -o /Users/niklas/Desktop/test/build/my_project/main
    niklas ~/Desktop/test $ ls build
    build.ninja my_project
    niklas ~/Desktop/test $ ls build/my_project/
    main obj

#### Additional Links

* [Changelog](docs/changelog.rst)
* [Documentation](http://craftr.readthedocs.org/en/latest/?badge=latest)
* [Craftr extension build modules](https://github.com/craftr-build/craftr/wiki/Craftr-Extensions)
* [Projects using Craftr](https://github.com/craftr-build/craftr/wiki/Projects-using-Craftr)

### Contribute

I welcome all contributions, feedback and suggestions! If you have any of
those or just want to chat, ping me on twitter [@rosensteinn][], by [mail][] or
open a [new issue][]!

### Requirements

- [Ninja][]
- [Python][] 3.4 or higher
- see [requirements.txt](requirements.txt)

### Installation

    pip install craftr-build

To install from the Git repository, use the `-e` flag to be able to update
Craftr by simply pulling the latest changes from the remote repository.

    git clone https://github.com/craftr-build/craftr.git && cd craftr
    pip install -e .

----

<p align="center">MIT Licensed &ndash; Copyright &copy; 2016  Niklas Rosenstein</p>

  [new issue]: https://github.com/craftr-build/craftr/issues/new
  [@rosensteinn]: https://twitter.com/rosensteinn
  [mail]: mailto:rosensteinniklas@gmail.com
  [Ninja]: https://github.com/ninja-build/ninja
  [Python]: https://www.python.org/

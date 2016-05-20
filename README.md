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

Craftr is built around Python-ish modules that we call Craftr modules or
scripts. There are two ways a Craftr module can be created:

1. A file named `Craftfile.py` with a `# craftr_module(...)` declaration
2. A file named `craftr.ext.<module_name>.py`

By default, Craftr will execute the `Craftfile.py` from the current
working directy if no different main module is specified with the `-m`
option. Below you can find a simple Craftfile that can build a C++ program
on any platform (that is supported by the Craftr STL).

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

To get you an idea of what's going on, we pass the `-v` flag to enable
more detailed output. What you see below is an example run on Windows:

    λ craftr -ev
    detected ninja v1.6.0
    $ cd "build"
    load 'craftr.ext.my_project'
    (craftr.ext.my_project, line 9): unused options for compile(): {'std'}
    exporting 'build.ninja'
    $ ninja -v
    [1/2] cl /nologo /c c:\users\niklas\desktop\test\src\main.cpp /Foc:\users\niklas\desktop\test\build\my_project\obj\main.obj /EHsc /W4 /Od /showIncludes
    [2/2] link /nologo c:\users\niklas\desktop\test\build\my_project\obj\main.obj /OUT:c:\users\niklas\desktop\test\build\my_project\main.exe

    λ ls build build\my_project\
    build:
    build.ninja  my_project/

    build\my_project\:
    main.exe*  obj/

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
* [Pandoc][] when installing from the Git repository

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
  [Python]: https://www.python.org
  [Pandoc]: http://pandoc.org

<h1>
  The Craftr build system
  <a href="https://travis-ci.org/craftr-build/craftr"><img alt="Build Status" src="https://travis-ci.org/craftr-build/craftr.svg?branch=master"/></a>
  <a href='http://craftr.readthedocs.org/en/latest/?badge=latest'>
    <img src='https://readthedocs.org/projects/craftr/badge/?version=latest' alt='Documentation Status' />
  </a>
  <img align="right" height="85" src="http://i.imgur.com/i3hYFZ3.png"/>
</h1>


Craftr is a build system based on [Ninja][] and [Python 3.4+][Python].

```python
# craftr_module(simple)
# A basic example to compile a C++ program on any supported platform.

from craftr import *
from craftr.ext.platform import cxx, ld

obj = cxx.compile(
  sources = path.glob('src/*.cpp')
)
program = ld.link(
  output = 'main',
  inputs = obj
)
```

__Key Features__

* Modular builds written in Python
* Combine them with [Tasks][docs_Tasks]
* Easily extensible framework
* Builtin support for C/C++ (MSVC, Clang-CL, GCC, LLVM), Java, C#, Flex, Yacc and ProtoBuf

__Upcoming Features__

- [ ] Cross-platform support for OpenCL, CUDA, Vala

__Additional Links__

* [Documentation](http://craftr.readthedocs.org/en/latest/?badge=latest)
* [Craftr extension build modules](https://github.com/craftr-build/craftr/wiki/Craftr-Extensions)
* [Projects using Craftr](https://github.com/craftr-build/craftr/wiki/Projects-using-Craftr)

__Requirements__

- [Ninja][]
- [Python][] 3.4 or higher
- see [requirements.txt](requirements.txt)

__Why another build tool?__

Because (imho) all other available options suck.

----

<p align="center">MIT Licensed -- Copyright &copy; 2015  Niklas Rosenstein</p>

  [Ninja]: https://github.com/ninja-build/ninja
  [Python]: https://www.python.org/
  [docs_Tasks]: http://craftr.readthedocs.org/en/latest/?badge=latest#tasks

<h1>
  Craftr
  <a href="https://travis-ci.org/craftr-build/craftr"><img alt="Build Status" src="https://travis-ci.org/craftr-build/craftr.svg?branch=master"/></a>
  <img align="right" height="85" src="http://i.imgur.com/i3hYFZ3.png"/>
</h1>


Meta build system based on [Ninja][] and [Python 3.4+][Python].

```python
# craftr_module(simple)
from craftr import *
from craftr.ext.platform cxx, ld

obj = cxx.compile(
  sources = path.glob('src/*.cpp')
)
program = ld.link(
  inputs = obj
)
```

__Key Features__

* Modular builds written in Python
* Combine them with [Tasks][wiki_Tasks]
* Easily extensible framework
* Builtin support for C/C++ (MSVC, GCC, LLVM), Java, C#, Flex, Yacc and ProtoBuf

__Upcoming Features__

- [ ] Cross-platform support for OpenCL, CUDA, Vala

__Additional Links__

* [Documentation](https://github.com/craftr-build/craftr/wiki)
* [Craftr extension build modules](https://github.com/craftr-build/craftr/wiki/Craftr-Extensions)
* [Projects using Craftr](https://github.com/craftr-build/craftr/wiki/Projects-using-Craftr)

__Requirements__

- [Ninja][]
- [Python][] 3.4 or higher
- see [requirements.txt](requirements.txt)

__Why another build tool?__

Because (imho) all other available options suck. And don't even get me
started 'bout IDEs.

----

<p align="center">MIT Licensed -- Copyright &copy; 2015  Niklas Rosenstein</p>

  [Ninja]: https://github.com/ninja-build/ninja
  [Python]: https://www.python.org/
  [wiki]: https://github.com/craftr-build/craftr/wiki
  [wiki_Tasks]: https://github.com/craftr-build/craftr/wiki/General#tasks

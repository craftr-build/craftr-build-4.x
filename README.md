__NAME__

`craftr` - build system based on [Ninja][] and [Python 3.4+][Python].

[![PyPI Version](https://badge.fury.io/py/craftr-build.svg)](https://pypi.python.org/pypi/craftr-build)

__DESCRIPTION__

Craftr is a cross-platform meta build system that features modular build
defintions, multiple abstraction layers, flexibility, extensibility, scalability
and performance. It can be used for any kinds of software build automation and
is not bound to a specific language domain.

__CONTRIBUTING__

I am developing this project in my free time. Contributions of any kind are
highly welcome. If you're having trouble getting started with Craftr, please
open a [new issue][].

__ADDITIONAL LINKS__

* [Documentation](http://craftr.readthedocs.org/en/latest/?badge=latest)
* [Craftr extension build modules](https://github.com/craftr-build/craftr/wiki/Craftr-Extensions)
* [Projects using Craftr](https://github.com/craftr-build/craftr/wiki/Projects-using-Craftr)

__DEPENDENCIES__

- [Ninja][]
- [Python][] 3.4 or higher
- see [requirements.txt](requirements.txt)

__INSTALLATION__

With Pip

    niklas@sunbird ~$ pip install craftr-build

Latest development version (editable, thus updatable with `git pull`)

    niklas@sunbird ~$ git clone https://github.com/craftr-build/craftr.git
    niklas@sunbird ~$ pip install -e craftr

__EXAMPLES__

A basic example to compile a C++ program on any of the support platforms.

```python
# craftr_module(simple)
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

Export and build with [Ninja][].

    $ craftr -eb
    [2/2] g++ simple/obj/main.o simple/obj/utils.o -o simple/main
    $ ls build
    build.ninja simple
    $ ls build/simple
    main obj

----

<p align="center">MIT Licensed &ndash; Copyright &copy; 2016  Niklas Rosenstein</p>

  [new issue]: https://github.com/craftr-build/craftr/issues/new
  [Ninja]: https://github.com/ninja-build/ninja
  [Python]: https://www.python.org/
  [docs_Tasks]: http://craftr.readthedocs.org/en/latest/?badge=latest#tasks

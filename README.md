<h1>The Craftr build system
<img align="right" height="100" src="http://i.imgur.com/i3hYFZ3.png"></h1>
[![Build Status](https://travis-ci.org/craftr-build/craftr.svg?branch=master)](https://travis-ci.org/craftr-build/craftr)
[![Code Issues](https://www.quantifiedcode.com/api/v1/project/e5f9d2e0933b4609844a98185f88b831/badge.svg)](https://www.quantifiedcode.com/app/project/e5f9d2e0933b4609844a98185f88b831)

Craftr is a meta build system that generates build files for the fast and
efficient [Ninja][] build tool. It uses Python scripts to define the build
commands and dependencies.

__Key Features__

* High flexibility due to the nature of a real programming language
* Builtin support for C/C++ (MSVC, GCC, LLVM), Java, C#, Flex, Yacc and ProtoBuf
* [Integrate tasks][Wiki_Tasks] and [Python scripts][Wiki_Python_Tools] in build definitions
* Build definitions in modules, make your own building blocks for large projects
* Easily extensible framework

__Additional Links__

* [Documentation](https://github.com/craftr-build/craftr/wiki)
* [Additional Craftr modules](https://github.com/craftr-build/craftr/wiki/Craftr-Extensions)
* [Projects using Craftr](https://github.com/craftr-build/craftr/wiki/Projects-using-Craftr)

  [Wiki_Tasks]: https://github.com/craftr-build/craftr/wiki/General#tasks
  [Wiki_Python_Tools]: https://github.com/craftr-build/craftr/wiki/Python-Tools

__Upcoming Features__

- [ ] Support for OpenCL, CUDA, Vala

__Requirements__

- [Ninja][]
- Python 3.4
- see [requirements.txt](requirements.txt)

__Why another build tool?__

Because I think most other available options sucks. That's why.

----

<p align="center">Copyright &copy; 2015  Niklas Rosenstein</p>

  [Ninja]: https://github.com/ninja-build/ninja
  [wiki]: https://github.com/craftr-build/craftr/wiki
  [craftr-daemon]: https://github.com/craftr-build/craftr/wiki/Call-Python-functions-from-Ninja

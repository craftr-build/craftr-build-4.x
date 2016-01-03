<h1>Craftr: Powerful meta build system for Ninja
<img align="right" height="100" src="http://i.imgur.com/i3hYFZ3.png"></h1>
[![Build Status](https://travis-ci.org/craftr-build/craftr.svg?branch=master)](https://travis-ci.org/craftr-build/craftr)

Craftr is a meta build system for [Ninja][] that uses Python to as its
build process description language. With a powerful programming language
at hand, custom software builds have never been so flexible and easy to
set up.

Please check out the [wiki][]!

__Features__

- Cross-platform compilation rules for MSVC, GCC and LLVM
- Built-in support for Java, C#, Flex, Yacc and ProtoBuf
- [Seamless integration of Python functions into the Ninja build chain][craftr-daemon]

__Upcoming Features__

- [ ] Support for OpenCL, CUDA, Vala

__Install__

Clone this repository and use `pip` to install Craftr, preferrably in a virtualenv and using
and editable installation. `pip -e .` does the trick.

__Requirements__

- [Ninja][]
- Python 3.4
- see [requirements.txt](requirements.txt)

----

<p align="center">Copyright &copy; 2015  Niklas Rosenstein</p>

  [Ninja]: https://github.com/ninja-build/ninja
  [wiki]: https://github.com/craftr-build/craftr/wiki
  [craftr-daemon]: https://github.com/craftr-build/craftr/wiki/Call-Python-functions-from-Ninja

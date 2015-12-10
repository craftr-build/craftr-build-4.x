<h1>Craftr: The better meta build system
<img align="right" height="100" src="http://i.imgur.com/i3hYFZ3.png"></h1>

Craftr is a meta build system for [Ninja][] that uses Python to as its
build process description language. With that powerful programming language
at hand, your builds have never been so flexible and easy at the same time.

Please check out the [wiki][]!

__Features__

- Compiler abstraction layers for MSVC, Gcc and Clang
- Support for compiling Java and C# code
- Invoke Python functions from the command-line, giving you the ability
  to run arbitrary tasks using the information from the build environment

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

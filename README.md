<img align="right" src="docs/logo.png">

## The Craftr build system

<a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-yellow.svg?style=flat-square"></a>
<img src="https://img.shields.io/badge/version-3.0.1--dev-blue.svg?style=flat-square"/>
<a href="https://travis-ci.org/craftr-build/craftr"><img src="https://travis-ci.org/craftr-build/craftr.svg?branch=master"></a>
<a href="https://ci.appveyor.com/project/NiklasRosenstein/craftr/branch/master"><img src="https://ci.appveyor.com/api/projects/status/6v01441cdq0s7mik/branch/master?svg=true"></a>

Craftr is a modular software build system written in Python that has native
support for C/C++, C#, Cython, Java and other languages. Craftr uses [Ninja]
as its build backbone.

  [Ninja]: https://github.com/ninja-build/ninja

[View the full documentation ▸](https://craftr-build.github.io/craftr)

### Current State

The core functionality is working and there is moderate support for C# and
Java, as well as some for C/C++, Haskell, OCaml and Vala &ndash; however the
interfaces for build scripts can change any time. The main goal at the moment
is to implement/improve support for the following languages:

* C/C++ (GCC, Clang, MSVC)
* Java (better Java 9 module support)

Some reference implementations are available in previous Craftr versions and
prototypes (namely [2.0], [v3.0.0-pre1] and [v3.0.0-pre2]).

  [2.0]: https://github.com/craftr-build/craftr/tree/2.0
  [v3.0.0-pre1]: https://github.com/craftr-build/craftr/tree/v3.0.0-pre1
  [v3.0.0-pre2]: https://github.com/craftr-build/craftr/tree/v3.0.0-pre2

---

<p align="center">Copyright &copy; 2015-2018 &nbsp; Niklas Rosenstein</p>

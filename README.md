<img align="right" src="logo.png">

## The Craftr build system

<a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-yellow.svg?style=flat-square"></a>
<img src="https://img.shields.io/badge/version-3.0.1--dev-blue.svg?style=flat-square"/>
<a href="https://travis-ci.org/craftr-build/craftr"><img src="https://travis-ci.org/craftr-build/craftr.svg?branch=master"></a>
<a href="https://ci.appveyor.com/project/NiklasRosenstein/craftr/branch/master"><img src="https://ci.appveyor.com/api/projects/status/6v01441cdq0s7mik/branch/master?svg=true"></a>

Craftr is a modular build system that has evolved from regular Python scripts
to a Domain Specific Language and has recently been inspired by [Buck],
[CMake] and [QBS]. It uses [Ninja] as its build backend by default, but
extensions can implement compatibility with other builders.  
Craftr runs on CPython 3.3 or higher.

  [Buck]: https://buckbuild.com/
  [CMake]: https://cmake.org/
  [QBS]: https://bugreports.qt.io/projects/QBS/summary
  [Ninja]: https://github.com/ninja-build/ninja.git
  [PyPI]: https://pypi.python.org/pypi

### Installation

Craftr 3 is in alpha and not currently available on [PyPI]. You can however
install it directly from the Git repository.

    pip3 install git+https://github.com/craftr-build/craftr.git@master


### What does it look like?

Craftr is supposed to be an ergonomic tool that should be easy to use and is
yet powerful and easy to extend/customize.

<table>
  <tr><th>C</th><th>C++</th></tr>
  <tr>
    <td>

```python
project "myproject"
using "cxx"
target "main":
  cxx.srcs = ['main.c']
```

Run as `craftr -cb main:cxx.run`
</td>
<td>

```python
project "myproject"
using "cxx"
target "main":
  cxx.srcs = ['main.cpp']
```

Run as `craftr -cb main:cxx.run`
</td>
  </tr>
  <tr><th>C#</th><th>Java</th></tr>
  <tr>
    <td>

```python
project "csharp_helloworld"
using "csharp"
target "main":
  csharp.srcs = glob('src/*.cs')
  csharp.packages = ['Newtonsoft.JSON:10.0.3']
  csharp.bundle = True
```

Run as `craftr -cb main:csharp.runBundle`
</td>
    <td>

```python
project "java_helloworld"
using "java"
target "main":
  java.srcs = glob('src/**/*.java')
  java.artifacts = [
      'org.tensorflow:tensorflow:1.4.0'
    ]
  java.mainClass = 'Main'
  java.bundleType = 'merge'  # Or 'onejar'
```

Run as `craftr -cb main:java.runBundle`
</td>
  </tr>
  <tr><th>Haskell</th><th>OCaml</th></tr>
  <tr>
    <td>

```python
project "haskell_helloworld"
using "haskell"
target "main":
  haskell.srcs = ['src/Main.hs']
```

Run as `craftr -cb main:haskell.run`
</td>
    <td>

```python
project "ocaml_helloworld"
using "ocaml"
target "main":
  ocaml.srcs = ['src/Main.ml']
  # False to produce an OCaml bytecode file
  ocaml.standalone = True
```

Run as `craftr -cb main:ocaml.run`
</td>
  </tr>
  <tr><th>Vala</th><th>Cython</th></tr>
  <tr>
    <td>

```python
project "vala_helloworld"
using "vala"
target "main":
  vala.srcs = ['src/Main.vala']
```

Run as `craftr -cb main:vala.run`
</td>
    <td>

```python
project "cython_helloworld"
using "cython"
target "main":
  cython.srcs = glob('src/*.pyx')
  cython.main = 'src/Main.pyx'
```

Run as `craftr -cb main:cython.run`
</td>
  </tr>
</table>

---

<p align="center">Copyright &copy; 2015-2018 &nbsp; Niklas Rosenstein</p>

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
# craftr -cb main:cxx.run
project "myproject"
using "cxx"
target "main":
  cxx.srcs = ['main.c']
```
</td>
<td>

```python
# craftr -cb main:cxx.run
project "myproject"
using "cxx"
target "main":
  cxx.srcs = ['main.cpp']
```
</td>
  </tr>
  <tr><th>C#</th><th>Java</th></tr>
  <tr>
    <td>

```python
# craftr -cb main:csharp.runBundle
project "csharp_helloworld"
using "csharp"
target "main":
  csharp.srcs = glob('src/*.cs')
  csharp.packages = ['Newtonsoft.JSON:10.0.3']
  csharp.bundle = True
```
</td>
    <td>

```python
# craftr -cb main:java.runBundle
project "java_helloworld"
using "java"
target "main":
  java.srcs = glob('src/**/*.java')
  java.artifacts = ['org.tensorflow:tensorflow:1.4.0']
  java.mainClass = 'Main'
  java.bundleType = 'merge'  # Or 'onejar'
```
</td>
  </tr>
  <tr><th>Haskell</th><th>OCaml</th></tr>
  <tr>
    <td>

```python
# craftr -cb main:haskell.run
project "haskell_helloworld"
using "haskell"
target "main":
  haskell.srcs = ['src/Main.hs']
```
</td>
    <td>

```python
# craftr -cb main:ocaml.run
project "ocaml_helloworld"
using "ocaml"
target "main":
  ocaml.srcs = ['src/Main.ml']
  ocaml.standalone = True  # False to produce an OCaml bytecode file
```
</td>
  </tr>
  <tr><th>Vala</th></tr>
  <tr>
    <td>

```python
# craftr -cb main:vala.run
project "vala_helloworld"
using "vala"
target "main":
  vala.srcs = ['src/Main.vala']
```
</td>
  </tr>
</table>

---

<p align="center">Copyright &copy; 2015-2018 &nbsp; Niklas Rosenstein</p>

<img align="right" src="logo.png">

## The Craftr build system

<a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-yellow.svg?style=flat-square"></a>
<img src="https://img.shields.io/badge/version-3.0.1--dev-blue.svg?style=flat-square"/>
<a href="https://travis-ci.org/craftr-build/craftr"><img src="https://travis-ci.org/craftr-build/craftr.svg?branch=master"></a>
<a href="https://ci.appveyor.com/project/NiklasRosenstein/craftr/branch/master"><img src="https://ci.appveyor.com/api/projects/status/6v01441cdq0s7mik/branch/master?svg=true"></a>

Craftr is a new software build system with a focus on ease of use, granularity
and extensibility. It is language independent and supports a wide range of
popular programming languages out of the box. Craftr uses [Ninja] to execute
builds.

  [Ninja]: https://github.com/ninja-build/ninja

### Current State

The core functionality is working and there is moderate support for C# and
Java, as well as some for C/C++, Haskell, OCaml and Vala &ndash; however the
interfaces for build scripts can change any time. The main goal at the moment
is to implement/improve support for the following languages:

* C/C++ (GCC, Clang, MSVC)
* Cython (requires C/C++ support)
* Java (better Java 9 module support)

Some reference implementations are available in previous Craftr versions and
prototypes (namely [2.0], [v3.0.0-pre1] and [v3.0.0-pre2]).

  [2.0]: https://github.com/craftr-build/craftr/tree/2.0
  [v3.0.0-pre1]: https://github.com/craftr-build/craftr/tree/v3.0.0-pre1
  [v3.0.0-pre2]: https://github.com/craftr-build/craftr/tree/v3.0.0-pre2

### How to Install  Craftr

  [Node.py]: https://github.com/nodepy/nodepy

Craftr builds on the [Node.py] runtime and must be installed via its package
manager `nodepy-pm`.

    $ pip install nodepy-runtime
    $ nodepy https://nodepy.org/install-pm.py
    $ nodepy-pm install git+https://github.com/craftr-build/craftr.git

---

### Examples

<table>
  <tr><th>C</th><th>C++</th></tr>
  <tr>
    <td>

```python
project "examples.c"
import "craftr/lang/cxx"
target "main":
  cxx.srcs = ['main.c']
```

Run as `craftr -cb main:cxx.run`
</td>
<td>

```python
project "examples.cpp"
import "craftr/lang/cxx"
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
project "examples.csharp"
import "craftr/lang/csharp"
target "main":
  csharp.srcs = glob('src/*.cs')
  csharp.packages = ['Newtonsoft.JSON:10.0.3']
  csharp.bundle = True
```

Run as `craftr -cb main:csharp.runBundle`
</td>
    <td>

```python
project "examples.java"
import "craftr/lang/java"
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
project "examples.haskell"
import "craftr/lang/haskell"
target "main":
  haskell.srcs = ['src/Main.hs']
```

Run as `craftr -cb main:haskell.run`
</td>
    <td>

```python
project "examples.ocaml"
import "craftr/lang/ocaml"
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
project "examples.vala"
import "craftr/lang/vala"
target "main":
  vala.srcs = ['src/Main.vala']
```

Run as `craftr -cb main:vala.run`
</td>
    <td>

```python
project "example.cython"
import "craftr/lang/cython"
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

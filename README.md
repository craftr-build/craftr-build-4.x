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

__Current State__

The build system core is running smoothly &ndash; now it is mostly a matter
of implementing support for various programming languages or extending the
features of existing supported languages (for example C/C++). Much of the
logic from previous Craftr versions ([2.0], [v3.0.0-pre]) can be used,
but the implementation will be very different.

  [2.0]: https://github.com/craftr-build/craftr/tree/2.0
  [v3.0.0-pre]: https://github.com/craftr-build/craftr/tree/v3.0.0-pre

__Install__

    $ pip install nodepy-runtime
    $ nodepy https://nodepy.org/instal-pm.py
    $ nodepy-pm install git+https://github.com/craftr-build/craftr.git

__Examples__

<table>
  <tr><th>C</th><th>C++</th></tr>
  <tr>
    <td>

```python
project "examples.c"
import "cxx.craftr"
target "main":
  cxx.srcs = ['main.c']
```

Run as `craftr -cb main:cxx.run`
</td>
<td>

```python
project "examples.cpp"
import "cxx.craftr"
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
import {glob} from "craftr.craftr"
import "csharp.craftr"
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
import {glob} from "craftr.craftr"
import "java.craftr"
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
import "haskell.craftr"
target "main":
  haskell.srcs = ['src/Main.hs']
```

Run as `craftr -cb main:haskell.run`
</td>
    <td>

```python
project "examples.ocaml"
import "ocaml.craftr"
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
import "vala.craftr"
target "main":
  vala.srcs = ['src/Main.vala']
```

Run as `craftr -cb main:vala.run`
</td>
    <td>

```python
project "example.cython"
import {glob} from "craftr.craftr"
import "cython.craftr"
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

<img align="right" src="logo.png">

## The Craftr build system

<a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-yellow.svg?style=flat-square"></a>
<img src="https://img.shields.io/badge/version-3.0.1--dev-blue.svg?style=flat-square"/>
<a href="https://travis-ci.org/craftr-build/craftr"><img src="https://travis-ci.org/craftr-build/craftr.svg?branch=master"></a>
<a href="https://ci.appveyor.com/project/NiklasRosenstein/craftr/branch/master"><img src="https://ci.appveyor.com/api/projects/status/6v01441cdq0s7mik/branch/master?svg=true"></a>

Craftr is a modular build system inspired by [Buck], [CMake], [QBS] and
previous versions of Craftr itself. It combines a declarative syntax
with the ability to evaluate Python code in the build script. The backbone
for the build process is [Ninja], however, extensions can be used to target
other build backends.

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

### Examples

#### C#

```python
# craftr --configure --build main:csharp.runBundle
project "csharp_helloworld"
target "main":
  dependency "csharp"
  csharp.srcs = glob('src/*.cs')
  csharp.packages = ['Newtonsoft.JSON:10.0.3']
  csharp.bundle = True
```

#### Java

```python
# craftr --configure --build main:java.runBundle
project "java_helloworld"
target "main":
  dependency "java"
  java.srcs = glob('src/**/*.java')
  java.artifacts = ['org.tensorflow:tensorflow:1.4.0']
  java.mainClass = 'Main'
  java.bundleType = 'merge'  # Or 'onejar'
```

#### OCaml

```python
# craftr --configure --build main:ocaml.run
project "ocaml_helloworld"
target "main":
  dependency "ocaml"
  ocaml.srcs = glob('src/*.ml')
  ocaml.standalone = True  # False to produce an OCaml bytecode file
```

---

<p align="center">Copyright &copy; 2015-2018 &nbsp; Niklas Rosenstein</p>

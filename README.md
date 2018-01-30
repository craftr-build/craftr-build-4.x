<img align="right" src=".assets/craftr-logo.png">

## The Craftr build system

<a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-yellow.svg?style=flat-square"></a>
<img src="https://img.shields.io/badge/version-3.0.0--dev-blue.svg?style=flat-square"/>
<a href="https://travis-ci.org/craftr-build/craftr"><img src="https://travis-ci.org/craftr-build/craftr.svg?branch=master"></a>
<a href="https://ci.appveyor.com/project/NiklasRosenstein/craftr"><img src="https://ci.appveyor.com/api/projects/status/6v01441cdq0s7mik?svg=true"></a>

Craftr is a modular build system inspired by [Buck], [CMake], [QBS] and
previous versions of Craftr itself. It combines a declarative syntax
with the ability to evaluate Python code in the build script. The backbone
for the build process is [Ninja], however, extensions can be used to target
other build backends.

  [Buck]: https://buckbuild.com/
  [CMake]: https://cmake.org/
  [QBS]: https://bugreports.qt.io/projects/QBS/summary
  [Ninja]: https://github.com/ninja-build/ninja.git

### Example

```python
project "myproject"

target "curlpp":
  dependency "cxx"
  export dependency "cxx/libs/curl"
  this.directory = "vendor/curlpp"
  cxx.type = 'library'
  cxx.srcs = glob('src/*.cpp')
  export cxx.includes = ['include']

target "main":
  dependency "cxx"
  dependency "@curlpp"
  cxx.srcs = glob('src/*.cpp')
  cxx.includes = ['include']
```

---

<p align="center">Copyright &copy; 2015-2018 &nbsp; Niklas Rosenstein</p>

# Projects using Craftr

## [NiklasRosenstein.cpp-nr](https://github.com/NiklasRosenstein/cpp-nr)

A simple C++ library with various components, complete with tests, benchmarks,
examples and continous integration. Demonstrates how to use Google Test and
Google Benchmark and how to implement a re-usable Craftr package. The library
can easily be used by using its Craftr Framework.

```python
cxx = load('craftr.lang.cxx')
cpp_nr = load('NiklasRosenstein.cpp-nr').nr

main = cxx.executable(
  output = 'main',
  inputs = cxx.compile_cpp(
    sources = glob('src/*.cpp'),
    frameworks = [cpp_nr]
  )
)
```

## [NiklasRosenstein.maxon.c4d](https://github.com/craftr-build/NiklasRosenstein.maxon.c4d)

A Craftr package that allows you to build C++ plugins for [MAXON Cinema 4D] on
Windows, macOS and Linux.

[MAXON Cinema 4D]: https://www.maxon.net/en/

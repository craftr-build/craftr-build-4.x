## examples/cython

This example demonstrates building a Cython application with Craftr.

### Build & Run

```
$ craftr -cf examples/cython/ -b main/Main:cxx.run
Selected compiler: gcc (gcc) ?? for x64
note: writing "build/debug/build.ninja"
note: Ninja v1.7.2 (/usr/bin/ninja)
[2/3] /usr/bin/python3 /home/niklas/Repositories/nodepy/nodepy/nodepy/main.py /home/niklas/Re...stdlib/craftr/backends/ninja/buildslave.py 'examples.cython@main/Main:cxx.run^b23177932e64' 0
[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181]
```

### Notes

* You can configure the Python distribution used when compiling the C/C++
  source files using the `craftr/lang/python:bin` option.
* You should select the appropriate Python distribution matching your build
  variant (debug, release) or the other way around.

### To do

* Source files listed in `cython.main` should be depending on C/C++ build
  products of `cython.srcs` (Craftr needs support for dependencies in the
  `BuildSet` class)
* Support `cython.inWorkingTree` option

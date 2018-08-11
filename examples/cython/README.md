### Example: `cython`

This example demonstrates building a Cython application with Craftr.

```
$ craftr -cb --project examples/cython/ --variant=release main:cxx.run
Selected compiler: Microsoft Visual C++ (msvc) 19.14.26433 for x64

======= BUILD

[examples.cython@main/cython.compile#1] SKIP
[examples.cython@main/Main/cxx.compileC#1] SKIP
[examples.cython@main/Main/cxx.link#1] SKIP
[examples.cython@main/Main/cxx.run#1] C:\Users\niklas\Desktop\craftr4\build\release\examples.cython\main\Main.exe
  $ 'C:\Users\niklas\Desktop\craftr4\build\release\examples.cython\main\Main.exe'
[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181]
```

#### Notes

* You can configure the Python distribution used when compiling the C/C++
  source files using the `craftr/lang/python:bin` option.
* You should select the appropriate Python distribution matching your build
  variant (debug, release) or the other way around.

#### To do

* Support `cython.inWorkingTree` option

# tiny-dnn

This package is a simple way to load the [tiny-dnn] headers into a Craftr
project. To verify that the library works fine on your system, you can do

    $ craftr export -m lib.cxx.tiny-dnn -d.build_examples -d.version=master
    running loaders for lib.cxx.tiny-dnn-1.0.0
      [+] source
        Downloading https://github.com/tiny-dnn/tiny-dnn/archive/master.zip
        Unpacking ".temp\tiny-dnn-master.zip" to "lib.cxx.tiny-dnn-1.0.0\src\tiny-dnn-master" ...
    lang.cxx: loading "lang.cxx.msvc" (with lang.cxx.msvc.toolkit="")
    lang.cxx:   cxc.name="msvc"
    lang.cxx:   cxc.target_arch="x64"
    lang.cxx:   cxc.version="19.00.23918"

    $ craftr build example
    [1/3] msvc compile (C:\Users\niklas\Desktop\build\lib.cxx.tiny-dnn-1.0.0\src\tiny-dnn-master\examples\main.obj)
    [2/3] msvc link (C:\Users\niklas\Desktop\build\lib.cxx.tiny-dnn-1.0.0\example.exe)
    [2/3] cmd /c cd C:\Users\niklas\Desktop\build\lib.cxx.tiny-dnn-1.0.0\src\tiny-dnn-master\examples && C:\Users\niklas\Desktop\build\lib.cxx.tiny-dnn-1.0.0\example.exe
    load models...
    start learning

    0%   10   20   30   40   50   60   70   80   90   100%
    |----|----|----|----|----|----|----|----|----|----|
    ********

  [tiny-dnn]: https://github.com/tiny-dnn/tiny-dnn

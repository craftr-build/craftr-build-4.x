### Example: `cpp-opencl`

This example uses the OpenCL 2.0 C++ bindings.

#### Note

On Windows, you may have to  specify your OpenCL vendor explicitly,
eg. `-Oopencl:vendor=intel`.

On some Linux systems, you may find that `pkg-config` can not find information
on the `OpenCL` package. In that case, you can override the information
returned by pkg-config using for example `-Opkg-config:OpenCL=-lOpenCL` or
even `-Opkg-config:OpenCL=-Wl,/usr/lib64/libOpenCL.so.1`.

#### Usage

```
$ craftr -cb --project examples/cpp-opencl main:cxx.run -Opkg-config:OpenCL=-lOpenCL
Selected compiler: gcc (gcc) ?? for x64
[examples.cpp-opencl@main/cxx.compileCpp#1] Building main.o
  $ g++ /home/niklas/Repositories/craftr/examples/cpp-opencl/main.cpp -c -o /home/niklas/Repositories/craftr/build/debug/examples.cpp-opencl/main/obj/main.o -g -MD -MP -MF /home/niklas/Repositories/craftr/build/debug/examples.cpp-opencl/main/obj/main.o.d
[examples.cpp-opencl@main/cxx.link#1]
  $ g++ -o /home/niklas/Repositories/craftr/build/debug/examples.cpp-opencl/main/main-1.0-0 /home/niklas/Repositories/craftr/build/debug/examples.cpp-opencl/main/obj/main.o -lOpenCL
[examples.cpp-opencl@main/cxx.run#1] /home/niklas/Repositories/craftr/build/debug/examples.cpp-opencl/main/main-1.0-0
  $ /home/niklas/Repositories/craftr/build/debug/examples.cpp-opencl/main/main-1.0-0
Using platform: Intel Gen OCL Driver
Using device: Intel(R) HD Graphics Kabylake ULT GT2
result: {99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99 99}
```

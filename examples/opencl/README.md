## Craftr Example: C++ OpenCL/OpenGL

This example is derived from Intel's "OpenCL-OpenGL Interop" example which
can be found [here](https://software.intel.com/en-us/intel-opencl-support/code-samples).
It can only be compiled on Windows using MSVC (not MinGW) due to its reliance
on the Windows API and Windows resource files.

__Building the Example__

To build the sample application, make sure to specify the OpenCL vendor of
which you have an SDK installed. Eg. to compile with the Intel SDK, use
`--options opencl.vendor=intel`.

__Running the Example__

When running the sample application, you may need to specify the `-p` argument
to choose the platform to run the OpenCL kernel on. The default value is
`"Intel"`. If you have an NVidia Graphics Card, you may need to use `-p NVIDIA`:

    $ cr -c examples/opencl/ --options opencl.vendor=nvidia -b :main_run="-p NVIDIA"

__Screenshot__

![](https://i.imgur.com/YuYYLcK.png)

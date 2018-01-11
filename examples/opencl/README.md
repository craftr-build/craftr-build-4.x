## Craftr Example: C OpenCL/OpenGL Mandelbrot

This example uses OpenCL and OpenGL interop to render the Mandelbrot set.
It shows usage of the following technologies/components:

* OpenGL
* OpenCL
* GLEW
* GLFW
* bin2c kernel and shader embedding

__Build__

On Windows, you may have to enable the `glfw.from_source` option and specify
your OpenCL vendor.

    $ craftr -c examples/opencl --options glfw.from_source opencl.vendor=intel
    $ craftr -b :main_run

__Screenshots__

![](https://i.imgur.com/zlbO7hP.png)

![](https://i.imgur.com/ImzYmAQ.png)

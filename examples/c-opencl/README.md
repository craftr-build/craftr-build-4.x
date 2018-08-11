### Example: `c-opencl`

This example uses OpenCL and OpenGL interop to render the Mandelbrot set.
It shows usage of the following technologies and Craftr build features:

* OpenGL/OpenCL/GLEW/GLFW
* Embedding kernel and shader programs using `cxx.embedFiles`

On Windows, you may have to enable the `craftr/libs/glfw:fromSource` option
and specify your OpenCL vendor, eg. `craftr/libs/opencl:vendor=intel`.

#### Screenshots

<table><tr><td>
<img src="https://i.imgur.com/zlbO7hP.png" height="400px">
</td><td>
<img src="https://i.imgur.com/ImzYmAQ.png" height="400px">
</td></tr></table>

####  To do

* Getting a `CL_INVALID_GL_SHAREGROUP_REFERENCE_KHR` error on Windows 10 with
  the NVIDIA CUDA OpenCL driver (GTX 780) and Intel Drivers (i7-4770K) but
  it works on Windows with an Intel i7-7500U.

* Ubuntu with Intel HD drivers: Getting `error: OpenGL=>OpenCL image could not be created: CL_MEM_OBJECT_ALLOCATION_FAILURE`.
  The `clCreateFromGLTexture2D()` function is not supposed to return this error per the specification.
  Already checked questions for solutions:

    * [AMD Forum: clCreateFromGLTexture2D + GL textures without mipmaps](https://community.amd.com/thread/136580):
      `glGenerateMipmaps(GL_TEXTURE_2D)` did not help.

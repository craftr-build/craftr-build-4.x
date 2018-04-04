+++
title = "GLFW"
+++

`craftr/libs/glfw`

### Notes

* When compiling from source, check the dependency information in the [GLFW
  documentation].

### To do

* Building from source on Linux rebuilds everything everytime after the
  build was reconfigured with the same settings (seems like some data is
  stored inconsistently eg. in an unordered set/map). Reproducible with
  `craftr -cf examples/c-opencl/ -o craftr/libs/glfw:fromSource=true -b main:cxx.link`

[GLFW documentation]: http://www.glfw.org/docs/latest/compile.html#compile_deps_x11

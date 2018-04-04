+++
title = "CMake"
+++

`craftr/libs/cmake`

This module provides the `configure_file()` option that can render a CMake
`.in` header file.

### API

#### `configure_file(input, output=None, environ={}, inherit_environ=True) -> ConfigResult`

#### `ConfigResult`

* `output` &ndash; The output file.
* `directory` &ndash; The output directory.

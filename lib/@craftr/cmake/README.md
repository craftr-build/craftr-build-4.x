## @craftr/cmake

This module provides some CMake-like functionality.

### Function `configure_file(input, output=None, environ={}, inherit_environ=True)`

Render a CMake template file using the specified *environ*. If
*inherit_environ* is enabled, the system environment variables will be
taken into account, too.

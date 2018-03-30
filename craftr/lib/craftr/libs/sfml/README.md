## SFML Bindings for Craftr

* Windows: Downloads the appropriate windows SFML binaries, unless the
  `craftr/libs/sfml:binaryDir` option is set.
* Linux/macOS:  Uses `pkg-config SFML-all`.

__Tested on__

* Windows 10

__Example build script__

```python
project "sfml-example"

target "main":
  requires "craftr/libs/sfml"
  cxx.srcs = ['main.cpp']
```

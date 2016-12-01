# Qt5

## Configure

Set `craftr.lib.qt5.path` option to the directory that contains the Qt5 prebuilt
binaries and header files.

Currently tested on Windows only.

## Compile

```python
load_module('craftr.lang.cxx.*')
qt5 = load_module('craftr.lib.qt5')

obj = cpp_compile(
  sources = glob(['src/*.cpp')],
  frameworks = [qt5.framework('Qt5Widgets', 'Qt5Multimedia')],
)

bin = cxx_binary(
  inputs = obj,
  output = 'main'
)
```

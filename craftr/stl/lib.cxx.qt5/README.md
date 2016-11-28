# Qt5

## Configure

Set `lib.cxx.qt5.path` option to the directory that contains the Qt5 prebuilt
binaries and header files.

Currently tested on Windows only.

## Compile

```python
qt5 = load_module('lib.cxx.qt5')

obj = cpp_compile(
  sources = glob(['src/*.cpp')],
  frameworks = [qt5.framework('Qt5Widgets', 'Qt5Multimedia')],
)

bin = cxx_binary(
  inputs = obj,
  output = 'main'
)
```

# C/C++ language support (`craftr.lang.cxx`)

Configuration:

- `.toolkit` &ndash; Name of the toolkit, decides which compiler interface to
  load. Currently support values are `clang`, `gcc`, `clang-cl`, `msvc` and
  `msvc-140` (replace `140` with a MSVC version number).

For toolkit-specific configuration, check out the respective compiler
interface module.

- [`craftr.lang.cxx.common`](../craftr.lang.cxx.common) for Clang/GCC
- [`craftr.lang.cxx.msvc`](../craftr.lang.cxx.msvc) for MSVC

Example:

```python
cxx = load('craftr.lang.cxx')

mylib = Framework(
  include = [local('include')],
  defines = ['HAVE_MYLIB']
)

_lib = cxx.static_library(
  inputs = cxx.compile_c(
    sources = glob(['src/**/*.c'], exclude = ['src/main.c']),
    frameworks = [mylib],
    std = 'c11'
  ),
  output = 'mylib'
)

cxx.extend_framework(mylib, _lib)

app = cxx.executable(
  inputs = cxx.compile_c(
    sources = [local('src/main.c')],
    frameworks = [mylib],
    std = 'c11'
  ),
  output = 'myapp'
)
```

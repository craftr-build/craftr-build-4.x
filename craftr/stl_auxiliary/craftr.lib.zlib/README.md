# zlib (`craftr.lib.zlib`)

&ndash; http://www.zlib.net/

```python
cxx = load_module('craftr.lang.cxx')
zlib = load_module('craftr.lib.zlib')

binary = cxx.binary(
  output = 'main',
  inputs = cxx.cpp_compile(
    sources = glob(['src/*.cpp']),
    frameworks = [zlib.zlib]
  )
)
```

# zlib (`craftr.lib.zlib`)

&ndash; http://www.zlib.net/

```python
cxx = load('craftr.lang.cxx')
zlib = load('craftr.lib.zlib')

binary = cxx.binary(
  output = 'main',
  inputs = cxx.cpp_compile(
    sources = glob(['src/*.cpp']),
    frameworks = [zlib.zlib]
  )
)
```

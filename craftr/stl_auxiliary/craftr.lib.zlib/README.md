# zlib (`craftr.lib.zlib`)

&ndash; http://www.zlib.net/

```python
cxx = load('craftr.lang.cxx')
zlib = load('craftr.lib.zlib')

binary = cxx.executable(
  output = 'main',
  inputs = cxx.compile_cpp(
    sources = glob(['src/*.cpp']),
    frameworks = [zlib.zlib]
  )
)
```

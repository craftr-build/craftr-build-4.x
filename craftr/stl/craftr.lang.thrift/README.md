# Apache Thrift

This package is incomplete.

## Todolist

- [ ] Support for automatically finding the required Thrift libraries
  or eventually downloading them automatically (?)
- [ ] Parse input thrift files to determine which output files will be
  generated (late feature)

## Example

Check out the `examples/examples.thrift` directory.

```python
# examples.thrift

load('craftr.lang.cxx.*')
load('craftr.lang.thrift.*')

thriftfiles = thrift_gen(
  inputs = [local('tutorial.thrift')],
  gen = ['cpp:pure_enums,movable_types', 'py:new_style,utf8strings'],
)

sources = [
  'thrift/Calculator.cpp',
  'thrift/tutorial_constants.cpp',
  'thrift/tutorial_types.cpp'
]

# NOTE: This currently does not work if the compiler can not find all of
# Thrift's dependencies by default.
lib = cxx_library(
  inputs = cpp_compile(
    sources = map(buildlocal, sources),
  ) << thriftfiles,
  output = 'thrift-tutorial'
)
```

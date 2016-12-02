# googletest

Craftr package for using googletest.

> __Note__: The googletest package is currently always compiled from source.

__Craftrfile__

```python
load_module('craftr.lib.googletest.*')

test = runtarget(
  cxx_binary(
    inputs = compile(sources = glob(['tests/*.cpp'], frameworks = [googletest])),
    output = 'test'
  )
)
```

__tests/main.cpp__

```cpp
#include <gtest/gtest.h>

// ...

int main(int argc, char** argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
```

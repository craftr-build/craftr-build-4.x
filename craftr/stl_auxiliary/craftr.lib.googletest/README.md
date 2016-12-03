# googletest

Use [googletest][] in your C++ project. This package will always download
a source archive from the Git repository and compile the libraries from source.
To use googletest, simply load this Craftr package and compile a test binary.

  [googletest]: https://github.com/google/googletest

## Usage

```python
load_module('craftr.lang.cxx.*')
load_module('craftr.lib.googletest.*')

test = runtarget(
  cxx_binary(
    inputs = compile(sources = glob(['tests/*.cpp'], frameworks = [googletest])),
    output = 'test'
  )
)
```

## Example

```cpp
#include <gtest/gtest.h>

TEST(simple, test) {
  ASSERT_TRUE(true);
}

int main(int argc, char** argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
```

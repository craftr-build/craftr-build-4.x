# googletest

Use [googletest][] in your C++ project. This package will always download
a source archive from the Git repository and compile the libraries from source.
To use googletest, simply load this Craftr package and compile a test binary.

  [googletest]: https://github.com/google/googletest

## Usage

```python
cxx = load('craftr.lang.cxx')
googletest = load('craftr.lib.googletest').googletest

main = cxx.executable(
  inputs = compile(sources = glob(['tests/*.cpp'], frameworks = [googletest])),
  output = 'test'
)
test = runtarget(main)
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

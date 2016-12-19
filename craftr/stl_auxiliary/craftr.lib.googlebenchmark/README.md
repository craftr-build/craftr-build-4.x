# google/benchmark

Use the Google [benchmark][] library in your C++ project.

Known Limitations:

- Currently only supports the C++11 `<regex>` backend

  [benchmark]: https://github.com/google/benchmark

## Usage

```python
load('craftr.lang.cxx.*')
load('craftr.lib.googlebenchmark.*')

test = runtarget(
  cxx_binary(
    inputs = compile(sources = glob(['benchmark/*.cpp'], frameworks = [googlebenchmark])),
    output = 'test'
  )
)
```

## Example

```cpp
static void BM_StringCreation(benchmark::State& state) {
  while (state.KeepRunning())
    std::string empty_string;
}
// Register the function as a benchmark
BENCHMARK(BM_StringCreation);

// Define another benchmark
static void BM_StringCopy(benchmark::State& state) {
  std::string x = "hello";
  while (state.KeepRunning())
    std::string copy(x);
}
BENCHMARK(BM_StringCopy);

BENCHMARK_MAIN();
```

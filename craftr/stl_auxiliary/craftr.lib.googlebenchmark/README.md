# google/benchmark

Use the Google [benchmark][] library in your C++ project.

Known Limitations:

- Currently only supports the C++11 `<regex>` backend

  [benchmark]: https://github.com/google/benchmark

## Usage

```python
cxx = load('craftr.lang.cxx')
googlebenchmark = load('craftr.lib.googlebenchmark').googlebenchmark

main = cxx.executable(
  inputs = cxx.compile_cpp(sources = glob(['benchmark/*.cpp'], frameworks = [googlebenchmark])),
  output = 'test'
)
test = runtarget(main)
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

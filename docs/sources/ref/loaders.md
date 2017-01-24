If you're project provides some examples that depend on huge binary data,
you can download these files when necessary:

```python
if options.build_examples:
  example_data = external_file("http://url.to/example/data.bin")
  # ... build examples here
```

Many build scripts for projects that are not usually built with Craftr
use the `external_archive()` function to download a source archive and
build from that.

```python
source_directory = external_archive(
  "https://curl.haxx.se/download/curl-{}.tar.gz".format(options.version)
)

# ...
```

For details on these functions, check the [Built-ins Documentation](builtins.md)
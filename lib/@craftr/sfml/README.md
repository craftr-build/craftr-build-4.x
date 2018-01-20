## SFML Bindings for Craftr

If the `sfml.binary_dir` option is not set, the appropriate windows SFML
binaries will be downloaded automatically.

__Todo__

* On Unix, try pkgconfig first

__Tested on__

* Windows 10

__Run the example__

    $ craftr --release -c craftr/libs/sfml/example -b :main_run

__Example build script__

```python
import craftr from 'craftr'
import cxx from 'craftr/lang/cxx'
import 'craftr/libs/sfml'

cxx.binary(
  name = 'main',
  deps = ['//craftr/libs/sfml:sfml'],
  srcs = ['main.cpp']
)

cxx.run(':main')
```


# Craftr 2.0.0-dev

Prototype for the next-level, more pythonic meta build system.

```python
# craftr_module(test)

from craftr import *
from craftr.path import glob
from craftr.shell import split

sources = glob('src/*.cpp')

foo = Target(
  command=split('gcc $in -o $out'),
  inputs=sources,
  outputs=['build/main'],
)
```

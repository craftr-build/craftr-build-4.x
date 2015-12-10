# Craftr: Meta build system for humans <img align="right" height="100" src="http://i.imgur.com/i3hYFZ3.png">

Craftr is a meta build system that targets [Ninja][] that uses Python to describe the build settings.

__Install__

Clone this repository and use `pip` to install Craftr, preferrably in a virtualenv and using
and editable installation. `pip -e .` does the trick.

__Requirements__

- [Ninja][]
- Python 3.4
- see [requirements.txt](requirements.txt)

__Examples__

To export a Ninja build manifest, use the `-e` option. The `-b` option automatically switches
into the build directory and runs ninja.

    craftr -eb

__C/C++__ (the plain method)

```python
# craftr_module(project)

from os import environ
from craftr import path, Target, platform
from craftr.ext.compiler import gen_objects

sources = path.glob('src/*.c')

objects = Target(
  command = [environ['CC']] + '-c -Wall $in -o $out'.split(),
  inputs = sources,
  outputs = gen_objects(sources, suffix=platform.obj),
)

```

__C/C++__

```python
# craftr_module(nr.test)

from craftr import path
from craftr.ext.compiler import get_platform_toolset

tools = get_platform_toolset()
cc = tools.CCompiler()
ld = tools.Linker()

objects = cc.compile(
  sources = path.glob('src/*.c'),
)

lib = ld.link(
  inputs = objects,
  output = 'main',
  output_type = 'bin',
)
```

> ### Todo
> 
> - [ ] GCC compiler interface
> - [ ] Clang compiler interface
> - [ ] `get_platform_toolset()` must detect the right compiler for the
>   platform and the environment (eg. based on the `CC` and `CXX` variables)

__C#__

```python
# craftr_module(project)

from craftr import path
from craftr.ext.compiler.csc import CSCompiler

csc = CSCompiler()

program = csc.compile(
  filename = 'main',
  sources = path.glob('src/**/*.cs'),
  optimize = True,
)
```

__Java__

```python
# craftr_module(project)

from craftr import path
from craftr.ext.compiler.java import JavaCompiler

javac = JavaCompiler()

classes = javac.compile(
  source_dir = path.local('src'),
)

jar = javac.make_jar(
  filename = 'my-jar-v1.0.0',
  classes = classes,
  entry_point = 'Main',
)
```

__Vala__

> __Todo__: Vala compiler interface.


  [Ninja]: https://github.com/ninja-build/ninja

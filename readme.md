# Craftr 0.20.0-dev

Prototype for the next-level, more pythonic meta build system.

# Examples

    python -m craftr -eb

> __Information__: `-e` for "export" and `-b` for "build".

## Example: C/C++ (the plain method)

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

## Example: C/C++

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

## Example: C# ##

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

## Example: Java

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

## Example: Vala

> __Todo__: Vala compiler interface.

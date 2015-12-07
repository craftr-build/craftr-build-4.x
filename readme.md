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

> __Todo__: A *good* interface for compiling C/C++ projects with proper
> implementations for GCC, Clang and MSVC (eventually also MinGW, Borland
> and Intel).

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

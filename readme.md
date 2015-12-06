# Craftr 2.0.0-dev

Prototype for the next-level, more pythonic meta build system.

## Example: C/C++ (the simple method)

```python
# craftr_module(project)

from os import environ
from craftr import path, Target

sources = glob('src/*.c')

objects = Target(
  command = [environ['CC'], '$in', '-c', '-o$out', '-I' + path.local('include')],
  inputs = sources,
  objects = path.setsuffix(path.move(sources, path.commonpath(sources), 'obj'), '.o'),
  foreach = True,
)
```

## Example: C/C++

> __Todo__: A *good* interface for compiling C/C++ projects with proper
> implementations for GCC, Clang and MSVC (eventually also MinGW, Borland
> and Intel).

## Example: C#

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

> __Todo__: Java compiler interface.

## Example: Vala

> __Todo__: Vala compiler interface.

# Craftr - Python meta build system

Craftr is a prototype and an attempted to create a meta build system
far superior to [Creator](https://github.com/creator-build/creator). 
Although Creator used Python to declare build rules, it didn't feel
pythonic at all. This should be different in Craftr.

### Basics

Similar to Creator, Craftr uses modules to divide namespaces. These
namespaces are however real Python object that can be accessed with
Python code and expose arbitrary data, functions and classes. To
create a module, we create a file called `Craftr` or that is suffixed
with `.craftr` and make sure to add a `craftr_module()` declaration
in its header.

```python
# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.
#
# craftr_module(my.library)

message = "Hello, World!"
```

A very interesting feature about Craftr is that the namespaces can
be accessed dotted in Python code, which was not possible in Creator.

```python
# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.
#
# craftr_module(app)

lib = load_module('my.library')

# Now we can use `lib` or `my.library` to access the module.
info(lib.message)
info(my.library.message)
```

### Options

In order to define options before a module is loaded, we can create
the namespace beforehand and assign values to it.

```python
lib = module.get_namespace('my.library')
lib.debug = True
load_module(lib)

info(lib.message)
```

We can also specify the option globally which can then be inherited
into the modules namespaces.

```python
G.debug = True
lib = load_module('my.library')

info(lib.message)
```

The module could either check if the `debug` variable was already
defined in its namespace using `try ... except` or using `setdefault()`
which would automatically check the global definitions as well.

```python
# craftr_module(my.library)

try:
  debug
except NameError:
  try:
    debug = G.debug
  except AttributeError:
    debug = False

# or rather using setdefault() which does exactly the same.
module.setdefault('debug', False)

if debug:
  message = "Hello, Debugger!"
else:
  message = "Hello, World!"
```

__Important__: Craftr has no support for lazy evaluation as with Creator.
That is why it is so important to be able to specify options to a module
before it is actually loaded as it can then take these options into
consideration.

### Targets

We can declare build targets using the `target()` function. The target
will automatically be assigned to a local variable in the modules namespace.
The command to build a file may contain the placeholders `'%%in'` and
`'%%out'` that will automatically be expanded by the backend.

```python
from craftr.utils.path import *
sources = glob(join(project_dir, '**', '*.cpp'))
objects = move(sources, project_dir, join(project_dir, 'build'), suffix='o')
program = join(project_dir, 'build', 'main')
module.target('Objects',
  inputs = sources,
  outputs = objects,
  foreach = True,
  command = ['g++', '-c', '%%in', '-o', '%%out'],
)
module.target('Program',
  inputs = objects,
  command = ['g++', '%%in', '-o', '%%out'],
)
```

__Important__: Make sure to use a target name that is not already
occupied by an existing variable as it would be overwritten and Craftr
will raise an exception in this case. Common notation would be CamelCase
for target names and lower\_underscore\_separated names for variables.

The `target()` function supports a keyword argument `target_class` that
you can pass a class that will be used instead of `craftr.runtime.Target`.
We plan on using this feature as a plugin-hook to change the behaviour
of targets.

----------

Copyright (C) 2015 Niklas Rosenstein

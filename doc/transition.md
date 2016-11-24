This document should give you a quick idea of how to transition your Craftr 1
build scripts to Craftr 2.x. Not too much has changed in terms of the build
scripts, mainly the way other scripts are imported is different.

Instead of using Python-style imports, you use the `load_module()` builtin
function in Craftr 2. Below we show the old and new way of importing the C/C++
target generators.

```python
from craftr.ext.platform import cc, cxx, ld, ar    # old
cxc = load_module('lang.cxx').cxc                  # new
```

However what we usually do in Craftr 2 now is to use star-imports to
load the contents of the module into the global namespace.

```python
load_module('lang.cxx.*')
```

## Doing the transition

Use the `craftr startpackage` command to create the manifest and build script
files in your project. If you want to keep your root directory clean, use the
`-n/--nested` option.

    $ cd my-project
    $ craftr startpackage my_project . --nested

Open the `manifest.json` file and make sure to include all the dependencies
that you need (eg. `"lang.cxx": "*"`). Craftr 2 refuses to load a module if
it is not defined in the package's dependencies.

Now you can basically copy the content from your old `Craftfile.py` to the
new `Craftrfile` and make the adjustments.

## Compiler abstraction changes

### C/C++

In Craftr 1, there were separate objects depending on what you wanted to
do: compile C, C++, link or create a static library. In Craftr 2, there is
one object that can do all of it: `cxc`. There have been some changes to
the `compile()` and `link()` interface, but the most important one is that
`compile()` now requires a `language` parameter which can be either one of
`'c', 'c++', 'asm'`.

The `lang.cxx` module provides the following three new functions that should
be used instead:

- `c_compile()`
- `cpp_compile()`
- `cxx_binary()`
- `cxx_link()`

Note that `cxx_link()` has a `link_style` parameter that is `'static'` by
default but can be set to `'shared'` to produce a shared library.

### Cython

The interface is pretty much the same, only `cythonc.compile_project()` is now
only `cythonc.compile()`. There are named wrapper available when using starred
imports, namely

- `cython_compile()`
- `cython_project()`

### Java

- `java_compile()`
- `java_jar()`

### C#

- `csharp_compile()`

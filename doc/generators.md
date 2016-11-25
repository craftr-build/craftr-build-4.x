Most of them time you will be using functions that generate build targets
from some input information instead of hardcoding the exact command-line
arguments for a target. These we call "target generators".

You can create a target manually with the `gentarget()` builtin function
very easily and this is useful if you need exact control over the command
that is run for the target.

```python
main = gentarget(
  commands = ['gcc $in -o $out'.split()],
  inputs = glob(['src/*.c']),
  outputs = ['main']
)
```

But that is of course not portable to platforms that do not have the GCC
compiler. Also, maybe you need some more logic to generate the build command,
and in that case you might also want to reuse that logic on another target.

## Simple target generator

So instead of hardcoding the command, let's wrap it in a function that
genereates it for us.

```python
def gcc_binary(sources, output, name=None):
  command = 'gcc $in -o $out'.split()
  return gentarget([command], sources, [output], name=gtn(name, 'gcc_binary'))

main = gcc_binary(
  sources = glob(['src/*.c']),
  output = 'main'
)
```

I think everything is here is straightforward, except maybe for the
`gtn(name, 'gcc_binary')` part. What this function does is deriving the name
of the target from the variable that the result of the function is assigned
to, in this case the target name will be `main` (prefixed with the identifer
of your Craftr package). We can however specify an alternative name for the
target with the *name* argument, or otherwise if the function is not assigned
to a variable and no *name* argument is specified, default to the specified
`'gcc_binary'` name (with some numeric suffix to avoid target name collision).

Now this was a lot to take into. You don't need to fully understand what's
happening, you only need to understand that `gtn()` is what is used to derive
target names from when implementing target generators.

## The TargetBuilder

The `TargetBuilder` class does a lot of stuff for us that is very useful when
implementing target generators. Most of the target generators provided by
Craftr's standard library use this class. It's constructor takes 4 important
arguments:

1. **name** -- The name of the target. Again, use `gtn(name, 'alternative')`
   as value for this parameter.
2. **option_kwargs** -- Optional, this is usually a dictionary of additional
   keyword arguments that have been passed when calling the target generator
   function. These keyword arguments are included into the `OptionMerge` that
   is created internally by the `TargetBuilder` (more on that later).
3. **frameworks** -- Optional, a list of `Framework` objects which are to be
   include in the `OptionMerge` that is created internally by the
   `TargetBuilder` (more on that later). Unlike the **option_kwargs**, these
   frameworks are inherited by the created `Target`
4. **inputs** -- Optional, inputs for the target. This can be a single `Target`
   object, or a list of mixed `Target` objects and strings which must be
   filenames. For every `Target` in this parameter, its output files are
   included in the list of input files (see `TargetBuilder.inputs`) and all
   frameworks from these targets are inherited (see `TargetBuilder.frameworks`).

Now after the `TargetBuilder` was created, it has three important methods:

- `get(key, default)` -- Get an option from the `OptionMerge` created by the
  `TargetBuilder`. This effectively returns the first value found for *key*
  in the **option_kwargs** and **frameworks** specified on construction as
  well as any inherited frameworks.
- `get_list(key)` -- Like `get()`, but this expects all values found under
  *key* to be lists and joins them all into one list. This is especially useful
  for specifying accumulating options like include directories, preprocessor
  defines, library search paths and link library names, etc.
- `build(commands, inputs=None, outputs=None, implicit_deps=None, order_only_deps=None, metadata=None, **kwargs)`
  -- Create a `Target` object. Basically all these arguments are passed to the
  `craftr.core.build.Target` constructor and the `TargetBuilder.name` is used as
  the targets name. Note that **commands** must always be a list of commands,
  and every command must be a list of strings (the arguments).

Looking at our above exaple, let's do it with a `TargetBuilder` and extend it
a bit further:

```python
def gcc_binary(sources, output, name=None, frameworks=(), **kwargs):
  builder = TargetBuilder(gtn(name, 'gcc_binary'), kwargs, frameworks, sources)
  output = buildlocal(path.addsuffix(output, platform.bin))
  command = ['gcc', '$in', '-o', '$out']
  for fn in builder.get_list('include'):
    command.append('-I' + fn)
  for define in builder.get_list('defines'):
    command.append('-D' + define)
  for lib in builder.get_list('libs'):
    command.append('-l' + lib)
  if builder.get('debug', False):
    command += ['-g', '-O0']
  return builder.build([command], outputs=[output])

some_library = Framework('some_library',
  include = [local('vendor/some_library/include')],
  defines = ['USE_SOME_LIBRARY=1'],
  libs = ['some_library']
)

main = gcc_binary(
  sources = glob(['src/*.c']),
  output = 'main',
  include = [local('include')],
  debug = True,
  frameworks = [some_library]
)
```

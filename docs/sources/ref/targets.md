# Targets

In Craftr, build targets are represented by the `craftr.core.build.Target`
class. Instances of this class are usually not created directly, but instead
by using a `craftr.targetbuilder.TargetBuilder` object. A target contains the
following information:

- A **name** that is unique to the entire build process. This name is exported
  as a phony target to the Ninja manifest, allowing you to specifically select
  the target to be built from the command-line.
- One or more **commands** that are executed by Ninja to create the *outputs*
  from the *inputs* (eg. compile a source file into an object file, link an
  executable, create an archive from a list of files, etc.)
- Lists of filenames for the **inputs** and **outputs**, **implicit_deps**
  and **order_only_deps**.
- A boolean flag that marks the Target as **explicit** (thus, it is only built
  when required by another target or specified on the command-line).
- A boolean flag that specifies whether the Target operates on the *inputs*
  and *outputs* in a **foreach** manner, or if the command is only executed.
- Optionally, **cwd**  as the path to an alternate working directory when the
  *commands* are executed.
- An **environ** dictionary with additional environment variables to be set
  before the *commands* are executed.
- A list of **frameworks** that should be taken into account when the Target is
  treated as an input to another target. See the [Frameworks]
  Documentation for more information.

... and a few more less commonly used things.

[Frameworks]: frameworks

## Using the TargetBuilder

Creating a Target directly is not very common as there is quite a few things
to handle to make Craftr's target generator functions as convenient as they
are. Many target generators support retrieving options from a list of
Frameworks and additionally from keyword-arguments specified to the generator
function.

This is an example function that uses the `TargetBuilder` to create a target
from a list of input source files and additional options.

```python
1)   def compile(sources, output, frameworks=(), name=None, **kwargs):
2)     builder = TargetBuilder(gtn(name, 'compile'), kwargs, frameworks, sources, [output])
3)     include = builder.get_list('include')
4)     debug = builder.get('debug', options.debug)

5)     command = ['gcc', '$in', '-o', '$out']
       command += ['-I{}'.format(x) for x in include]
       if debug:
         command += ['-g', '-O0']

6)     return builder.build([command])
```

Let's look at what's happening here step-by-step.

1. `def compile()` defines a new Python function. It accepts 4 positional
   arguments, two of which must always be specified. Also, it accepts
   arbitrary keyword arguments. These will be taken into account together with
   the [Frameworks] and take absolute precedence should a parameter appear
   multiple times.
2. We create a TargetBuilder with all that information. Note how we use
   `gtn(name, 'compile')` to find the actual target name. It will attempt
   to determine the name from the variable that the result of `compile()`
   is being assigned. If it can not, it will default to the name `'compile_XXXX'`
   where `XXXX` is a numeric suffix to avoid collisions.
3. We retrieve the option `include` from the `**kwargs` and the `frameworks`
   that have been passed to the `compile()` function. Using `get_list()` will
   concatenate all values that can be found in all Frameworks.
4. We retrieve the option `debug`. This will return the first value that is
   found, or otherwise the second argument as a fallback (defaults to `None`).
   Note that we can only use `options.debug` if it has been specified as an
   option in the manifest of our package that provides the `compile()` function.
5. Create some useful command to compile the source files. Note how `$in` and
   `$out` are used to reference the *inputs* and *outputs*.
6. Create the actual Target from the specified list of commands (since we only
  have a single command, we have to wrap it in an additional list).

The `compile()` function could then be called like this:

```python
curl = pkg_config('curl')

main = compile(
  sources = glob('src/*.c'),
  output = 'main',
  include = [local('include')],
  debug = True,
  frameworks = [curl]
)
```

Note that if you pass keyword parameters that are not actually handled in the
target generator function (ie. with `builder.get()` or `get_list()`), Craftr
will print a warning that the parameter is unused.

!!! note

    The above example would only work on a platform that provides GCC,
    pkg-config and the cURL library.

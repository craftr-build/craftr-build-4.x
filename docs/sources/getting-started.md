> __Note__: The example we create in this tutorial can also be found in the
> [examples/examples.c](/examples/examples.c) folder.

Every project that is compiled with Craftr needs at least a manifest and a
build script. Craftr provides a convenient way to generate a template for you.
Choose your project directory and run the following command:

    $ craftr startpackage examples.c .
    $ ls
    Craftrfile  manifest.json
    $ cat Craftrfile
    # examples.c
    $ cat manifest.json
    {
      "name": "examples.c",
      "version": "1.0.0",
      "author": "",
      "url": "",
      "dependencies": {},
      "options": {}
    }

We're going to compile some C source files into an executable program. For
that we need the `craftr.lang.cxx` package that provides us with a
cross-platform interface to compile C and C++ source code. Open the
`manifest.json` and add `craftr.lang.cxx` to the dependencies.

```json
$ cat manifest.json
{
  "name": "examples.c",
  "version": "1.0.0",
  "author": "",
  "url": "",
  "dependencies": {
    "craftr.lang.cxx": "1.x"
  },
  "options": {}
}
```

> The `"1.x"` part is a version selector that specifies the version of the
> package that we depend on. We use `1.x` to denote that we accept any version
> which a major version number of `1`. For more information on version
> selectors, check out the [`VersionSelector` documentation][VersionSelector].

  [VersionSelector]: https://github.com/NiklasRosenstein/py-nr/blob/b26ceffbd8722e535c49fc6f74715d5a0641a35e/nr/types/version.py#L268-L283

Now let's assume we have the following two C source files in our project
directory as well.

```c
$ cat src/main.c

extern void say_hello(char const* name, char const* weather);

int main(int argc, char** argv) {
  if (argc != 3) {
    printf("error: usage: %s name weather\n");
    return 0;
  }
  say_hello(argv[1], argv[2]);
  return 0;
}

$ cat src/hello.c

#include <stdio.h>

void say_hello(char const* name, char const* weather) {
  printf("Hello, %s. You are facing a %s day\n", name, weather);
}
```

We want our build script to compile these two files into object files and then
link them together into an executable. Additionally, the build script should
allow us to make a test run of the program.

```python
$ cat Craftrfile
# examples.c

from os import environ
load_module('craftr.lang.cxx.*')

program = cxx_binary(
  inputs = c_compile(sources = glob(['src/*.c'])),
  output = 'main'
)

run = runtarget(program, environ.get('USERNAME', 'John'), "sunny")
```

And that's it. To compile our program, we first need to export a Ninja build
manifest, then we can build it. Our `run` target is explicit by default, meaning
that Ninja will not run it unless it is specified as an input or specified as
a target to build on the command-line.

    $ craftr export
    craftr.lang.cxx: loading "craftr.lang.cxx.msvc" (with craftr.lang.cxx.msvc.toolkit="")
    craftr.lang.cxx:   cxc.name="msvc"
    craftr.lang.cxx:   cxc.target_arch="x64"
    craftr.lang.cxx:   cxc.version="19.00.23918"
    $ craftr build
    [1/3] msvc compile (C:\Users\niklas\Desktop\test\build\examples.c-1.0.0\obj\src\main.obj)
    [2/3] msvc compile (C:\Users\niklas\Desktop\test\build\examples.c-1.0.0\obj\src\hello.obj)
    [3/3] msvc link (C:\Users\niklas\Desktop\test\build\examples.c-1.0.0\main.exe)
    $ craftr build run
    [0/1] C:\Users\niklas\Desktop\test\build\examples.c-1.0.0\main.exe niklas sunny
    Hello, niklas. You are facing a sunny day

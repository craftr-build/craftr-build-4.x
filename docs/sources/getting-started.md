> __Note__: The example we create in this tutorial can also be found in the
> [examples/examples.c](/examples/examples.c) folder.

Every project that is compiled with Craftr needs at least a manifest and a
build script. Craftr provides a convenient way to generate a template for you.
Choose your project directory and run the following command

    $ craftr startpackage examples.c .

Then open the `manifest.cson` file that was created and add the generic C/C++
module as a dependency. With `"*"` we specify that the newest version of the
module that is available should be used.

```cson
name: "examples.c"
version: "1.0.0"
dependencies:
  "craftr.lang.cxx": "*"
options:
```

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

cxx = load('craftr.lang.cxx')

program = cxx.binary(
  inputs = cxx.c_compile(sources = glob(['src/*.c'])),
  output = 'main'
)

from os import environ
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

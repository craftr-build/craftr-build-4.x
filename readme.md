> If you're looking for the latest stable version of Craftr, check out the [4.x][] branch.

  [4.x]: https://github.com/craftr-build/craftr-build/tree/4.x

# craftr-build

Frontend for the Craftr build framework.

__Requirements__

* Python 3.8+

## Getting started

Builds in Craftr are described using the Craftr DSL or plain Python in a file called
`build.craftr` or `build.craftr.py`, respectively. DSL code is transpiled into pure
Python code, so everything you can do in the DSL you can also do in Python, though it
is usually more convenient to use the DSL.

Most commonly, the first thing to do in the build script is to apply a plugin. Plugins
provide the means to describe specific build tasks. They do so by registering named extensions
to the `project` object, which in the Craftr DSL is used implicitly to resolve variables.

We'll use the `cxx` plugin to define a build task for a C program and the `run` plugin to
add a non-default task to execute the built program.

<table align="center">
  <tr><th>Craftr DSL</th><th>Python</th></tr>
  <tr><td>

  ```py
  apply 'cxx'
  apply 'run'

  cxx.compile {
    sources = glob('src/**/*.cpp')
    produces = 'executable'
  }

  run {
    dependencies.append tasks.compile
  }
  ```
  </td><td>

  ```py
  project.apply('cxx')
  project.apply('run')

  compile_task = project.cxx.compile()
  compile_task.sources = project.glob('src/**/*.cpp')
  compile_task.produces = 'executable'
  compile_task.finalize()

  run_task = project.run()
  run_task.dependencies.append(compile_task)
  run_task.finalize()
  ```
  </td></tr>
</table>

The build can then be executed using the Craftr CLI.

    $ craftr run
    > Task my-project:compile
    > Task my-project:run
    Hello, World!

---

<p align="center">Copyright &copy; 2021 &ndash; Niklas Rosenstein</p>

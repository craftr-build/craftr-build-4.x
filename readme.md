# craftr

Craftr is a Gradle-like build-system implemented in Python.

__Requirements__

* Python 3.9 or newer

## Getting started

Builds in Craftr are described using the Craftr DSL or plain Python in a file called
`build.craftr` or `build.craftr.py`, respectively. DSL code is transpiled into pure
Python code, so everything you can do in the DSL you can also do in Python, though it
is usually more convenient to use the DSL.

Most commonly, the first thing to do in the build script is to apply a plugin. Plugins
provide functionality to describe build tasks for languages.

<table align="center">
  <tr><th>Craftr DSL</th><th>Python</th></tr>
  <tr><td>

  ```py
  apply 'cxx'
  apply 'run'
  ```
  </td><td>

  ```py
  project.apply('cxx')
  project.apply('run')
  ```
  </td></tr>
</table>

Plugins register extensions to the project object which can be accessed through the `project`
object (which is accessed implicitly in the DSL if the variable cannot be otherwise resolved).

<table align="center">
  <tr><th>Craftr DSL</th><th>Python</th></tr>
  <tr><td>

  ```py
  cxx.compile {
    sources = glob('src/**/*.cpp')
    produces = 'executable'
  }
  ```
  </td><td>

  ```py
  compile_task = project.cxx.compile()
  compile_task.sources = project.glob('src/**/*.cpp')
  compile_task.produces = 'executable'
  compile_task.finalize()
  ```
  </td></tr>
</table>

Some built-in extensions are available by default through the `defaults` plugin, such
as the `run` task builder which executes the product of task that provides an executable.

<table align="center">
  <tr><th>Craftr DSL</th><th>Python</th></tr>
  <tr><td>

  ```py
  run {
    dependencies.append tasks.compile
  }
  ```
  </td><td>

  ```py
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

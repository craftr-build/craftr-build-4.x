The Craftr build system
=======================

Craftr is a next generation build system based on `Ninja`_ and `Python`_.
And don't worry, it isn't like waf or SCons!

.. raw:: html

  <style>.craftr-feature-table tr td:nth-child(2) { white-space: normal; }</style>
  <table class="docutils craftr-feature-table">
    <thead><tr><th colspan="2">Features</th></tr></thead>
    <tr>
      <td>Cross-platform</td>
      <td>Use Craftr anywhere Ninja and Python can run</td>
    </tr>
    <tr>
      <td>Modular build scripts</td>
      <td>Import other build scripts as Python modules, synergizes well
          with <code>git submodule</code></td>
    </tr>
    <tr>
      <td>Performance</td>
      <td>Craftr outperforms traditional tools like Make, CMake or Meson</td>
    </tr>
    <tr>
      <td>Language-independent</td>
      <td>Don't be tied to a single language, use Craftr for anything you want!</td>
    </tr>
    <tr>
      <td>Extensive standard library</td>
      <td>High-level interfaces to modern C/C++ compilers, C+, Java, Protobuff,
          Yacc, Cython, Flex, NVCC (OpenCL coming soon)</td>
    </tr>
    <tr>
      <td>Everything under your control</td>
      <td>Use the lowlevel API when- and wherever you need it and manully
          define the exact build commands</td>
    </tr>
    <tr>
      <td>Consequent out-of-tree builds</td>
      <td>Craftr never builds in your working tree (unless you tell it to)</td>
    </tr>
  </table>

Requirements
------------

- `Ninja`_
- `Python`_ 3.4 or newer

Contents
--------

.. toctree::
  :maxdepth: 1

  changelog
  cmd
  api
  stl
  ext
  rts
  magic

Getting Started
---------------

Craftr is built around Python-ish modules that we call Craftr modules or
Craftfiles (though this name usually refers to the first type of Craftr
modules). There are two ways a Craftr module can be created:

1. A file named ``Craftfile.py`` with a ``# craftr_module(...)`` declaration
2. A file named ``craftr.ext.<module_name>.py`` where ``<module_name>`` is
   of course the name of your Craftr module

By default, Craftr will execute the ``Craftfile.py`` from the current
working directy if no different main module is specified with the ``-m``
option. Below you can find a simple Craftfile that can build a C++ program
on any platform (that is supported by the Craftr STL).

.. code-block:: python

  #craftr_module(my_project)

  from craftr import path
  from craftr.ext.platform import cxx, ld

  # Create object files for each .cpp file in the src/ directory.
  obj = cxx.compile(
    sources = path.glob('src/*.cpp'),
    std = 'c++11',
  )

  # Link all object files into an executable called "main".
  program = ld.link(
    output = 'main',
    inputs = obj
  )

Below is a sample invokation on Windows. We pass the ``-v`` flag for
additional debug output by Craftr and full command-line output from Ninja.

::

  λ craftr -v
  detected ninja v1.6.0
  cd "build"
  load 'craftr.ext.my_project'
  (craftr.ext.my_project, line 9): unused options for compile(): {'std'}
  exporting 'build.ninja'
  $ ninja -v
  [1/2] cl /nologo /c c:\users\niklas\desktop\test\src\main.cpp /Foc:\users\niklas\desktop\test\build\my_project\obj\main.obj /EHsc /W4 /Od /showIncludes
  [2/2] link /nologo c:\users\niklas\desktop\test\build\my_project\obj\main.obj /OUT:c:\users\niklas\desktop\test\build\my_project\main.exe

  λ ls build build\my_project\
  build:
  build.ninja  my_project/

  build\my_project\:
  main.exe*  obj/


Installation
------------

::

    pip install craftr-build

To install from the Git repository, use the ``-e`` flag to be able to update
Craftr by simply pulling the latest changes from the remote repository.

::

    git clone https://github.com/craftr-build/craftr.git && cd craftr
    pip install -e .

Targets
-------

Craftr describes builds with the :class:`craftr.Target` class. Similar to
rules in Makefiles, a target has input and output files and a command to
produce the output files. Note that in Craftr, targets can also represents
`Tasks`_ which can be used to embed real Python functions into the build
graph.

Using the :class:`Target<craftr.Target>` class directly is usually not
necessary unless you have very specific requirements and need control
over the exact commands that will be executed. Or if you're just being
super lazy and need the easiest script to compile a C program:

.. code:: python

  # craftr_module(super_lazy)
  from craftr import Target, path
  main = Target(
    command = 'gcc $in -o $out',
    inputs  = path.local(['src/main.c', 'src/util.c']),
    outputs = 'main'
  )

The substition of ``$in`` and ``$out`` is conveniently done by `Ninja`_.

::

  $ craftr .main
  [1/1] gcc /home/niklas/Desktop/example/src/main....til.c -o /home/niklas/Desktop/example/build/main

Tasks
-----

Tasks were initially designed as functions doing convenient operations
that can be invoked from the command-line, they can also be used to export
any function as a "command" to the Ninja manifest and have the production
of output files implemented in Python.

A common use-case for tasks is to generate an archive from the build
products to have it ready for distribution. Below you can find a simple
example using the :mod:`archive<craftr.ext.archive>` and :mod:`git<craftr.ext.git>`
extension modules:

.. code:: python

  #craftr_module(myapp)
  from craftr import path, task, info
  from craftr.ext import archive, git, platform

  git = git.Git(project_dir)
  obj = platform.cc.compile(sources = path.glob('src/*.c'))
  bin = platform.ld.linkn(inputs = obj, output = 'myapp')

  @task(requires = [bin])
  def archive():
    archive = Archive(prefix = 'myapp-{}'.format(git.describe()))
    archive.add('res')        # Add a directory to the archive
    archive.add(bin.outputs)  # Add the produced binary
    archive.save()
    info('archive saved: {!r}'.format(archive.name))

.. note::

  Craftr is clever enough to run a task directly if it doesn't
  need any Ninja targets to be built before it can be executed.
  For example, the following task via ``craftr .hello``

  .. code:: python

    @task
    def hello():
      info('Hello, World!')

.. seealso::

  Tasks invoked by Ninja are executed through the :doc:`rts`.

Generator Functions
-------------------

Most of the time you don't want to be using `Targets`_ directly but instead
use functions to produce them with a high-level interface. It is sometimes
useful to create such a target generator function first and then use it
to reduce the complexity of the build script.

The Craftr standard library provides an extensive set of functions and
classes that generate targets for you, most notably the C/C++ compiler
toolsets.

.. seealso::

  Since C/C++ builds are very complex and strongly vary between platforms,
  Craftr defines a standard interface for compiling C/C++ source files as
  well as the linking and archiving steps.

  * :ref:`platform_interface`
  * :ref:`compiler_interface`
  * :ref:`linker_interface`
  * :ref:`archiver_interface`

Functions that generate targets use the :class:`craftr.TargetBuilder`
that does a lot of useful preprocessing and, as the name suggests,
make building `Targets`_  much easier.

Frameworks
----------

The :class:`craftr.Framework` is in fact just a dictionary (with an
additional :attr:`name<craftr.Framework>` attribute) that represents
a set of options for anything build related. How the data is interpreted
depends on the generator function.

Frameworks are useful for grouping build information. They were designed
for C/C++ builds but may find other uses as well. For example, there
might be a framework for a C++ library that specifies the include paths,
preprocessor definitions, linker search path and other libraries required
for the library to be used in a C++ application.

For example, the Craftfile for a header-only C++ library might look as
simple as this:

.. code:: python

  from craftr import Framework, path
  from craftr.ext.libs.some_library import some_library
  my_library = Framework(
    frameworks = [some_library],
    include = [path.local('include')],
    libs = ['zip'],
  )

As you can see in the example above, frameworks can also be nested.

Targets there were generated by helper functions (as described in
the `Generator Functions`_ section) list up the frameworks that have
been used to produce the target in the :attr:`Target.frameworks<craftr.Target.frameworks>`
attribute. Passing a target directly as input to another generator
function will automatically inherit the frameworks of that target!

.. code:: python

  fw = Framework(
    include = [path.local('vendor/include'),
    libpath = [path.local('vendor/lib')],
    libs = ['vendorlib1', 'vendorlib2']
  )

  obj = cc.compiler(
    sources = path.glob('src/*.c'),
    frameworks = [fw]
  )

  bin = ld.link(
    inputs = obj
    # we don't need to specify "fw" again, it is inherited from "obj"
  )

Build Options
-------------

Options for the build process are entirely read from environment variables.
The :func:`craftr.options.get` function is a convenient method to read the
options from the environment.

In Craftr, options can be specified local for a module or globally for
all modules. A local option is actually prefixed by the full name of
the Craftr module.

.. code:: python

  #craftr_module(app)
  from craftr import options
  name = options.get('name')
  debug = options.get_bool('debug')

  info('Hello {}, you want a {} build?'.format(name, 'debug' if debug else 'release'))

The options can be specified locally using the following methods:

::

  craftr -D.name="John Doe" -D.debug
  craftr -Dapp.name="John Doe" -Dapp.debug
  app.name="John Doe" app.debug="true" craftr   # assuming your shell supports this syntax

They can be set globally like this:

::

  craftr -Dname="John Doe" -Ddebug
  name="John Doe" debug="true" craftr   # assuming your shell supports this syntax

Options and environment variables can also be set from ``craftrc.py`` files.

Oh, and say hello to John!

::

  Hello John Doe, you want a debug build?

craftrc.py Files
-----------------

Before anything, Craftr will execute a ``craftrc.py`` file if any exist. This
file can exist in the current working directory and/or the users home directory.
Both will be executed if both exist! You can prevent Craftr from executing
these files by passing ``--no-rc``. You can also tell it to execute a specific
file with the ``--rc`` parameter (can be combined).

This file is not executed in a Craftr module context and hence should not
declare any targets, but it can be used to set up environment variables and
options.

For example, for using the `craftr.ext.qt5`_ module on Windows, you could
use this ``craftrc.py`` file in the home directory to let the Craftr Qt5
module know where the Qt5 headers and libraries are located.

.. code-block:: python

  from os import environ
  if 'Qt5Path' not in environ:
    environ['Qt5Path'] = 'D:\\lib\\Qt\\5.5\\msvc2013_64'

Note that you can still specify a different ``Qt5Path`` via the command
line that will override the value set in the ``craftrc.py`` file because
the environment variables are set in the following order:

1. Variables from the parent process/shell
2. Variables prefixed on the command-line (like ``VAR=VALUE craftr ...``)
   if your shell supports it
3. ``craftrc.py`` files that modify the :data:`craftr.environ`
4. Options passed via the ``-D, --define`` command-line parameter
5. Craftr modules that modify the :data:`craftr.environ`

Colorized Output
----------------

Craftr colorizes output by default if it is attached to a TTY. If it is not
but colorized output is still desired, ``CRAFTR_ISATTY`` can be set to ``true``
in the environment. Also, colorized output can be disabled by setting the
variable to ``false`` instead. For any other value, default behaviour applies.

Debugging
---------

Not only can you debug your Craftr build scripts with the :mod:`pdb`
module, but you can also increase the verbosity level to increase
the output detail. By default, Craftr already shows the module and
line number when using the :func:`craftr.info`, :func:`craftr.warn`
or :func:`craftr.error` functions. However, there might be cases
where you are facing messages as such and you don't know from where
exactly they originate.

::

    craftr: [INFO ]: Changed directory to "build"
    craftr: [WARN ] (options|L23): craftr.ext.options will be removed in the next version
    craftr: [WARN ] (options|L24): use craftr.options instead

Simply pass the ``-vv`` option to show stacktrace with each message.
Also note that this stacktrace is nicely highlighted if you're in a
terminal that supports ANSI color codes.

::

    craftr: [DEBUG]: Detected ninja v1.6.0
    craftr: [INFO ]: Changed directory to "build"
    craftr: [WARN ] (options|L23): craftr.ext.options will be removed in the next version
      In _load_backward_compatible() [<frozen importlib._bootstrap>|L634]
      In load_module() [/Users/niklas/Documents/craftr/craftr/ext.py|L225]
      In <craftr.ext.options> [/Users/niklas/Documents/craftr/craftr/lib/options.craftr|L23]
    craftr: [WARN ] (options|L24): use craftr.options instead
      In _load_backward_compatible() [<frozen importlib._bootstrap>|L634]
      In load_module() [/Users/niklas/Documents/craftr/craftr/ext.py|L225]
      In <craftr.ext.options> [/Users/niklas/Documents/craftr/craftr/lib/options.craftr|L24]

You can also use a verbosity level of one by passing only one ``-v``
and Craftr will only show the stack trace of :func:`craftr.error`
messages.

Additional Links
----------------

* `Craftr extension modules`_
* `Projects using Craftr`_

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _Ninja: https://github.com/ninja-build/ninja
.. _Python: https://www.python.org/
.. _Pip: https://pypi.python.org/pypi/pip
.. _virtualenv: http://docs.python-guide.org/en/latest/dev/virtualenvs/
.. _craftr.ext.qt5: https://github.com/craftr-build/qt5
.. _Craftr extension modules: https://github.com/craftr-build/craftr/wiki/Craftr-Extensions
.. _Projects using Craftr: https://github.com/craftr-build/craftr/wiki/Projects-using-Craftr
.. _nr_matrix: https://github.com/NiklasRosenstein/nr_matrix

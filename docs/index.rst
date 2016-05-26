The Craftr build system
=======================

Craftr is the build system of the future based on `Ninja`_ and `Python`_.

* Modular build scripts
* Cross-platform support
* Low- and high-level interfaces for specifying build dependencies and commands
* Good performance compared to traditional build systems like CMake and Make or Meson
* LDL: Language-domain-less, Craftr is an omnipotent build system
* Extensive STL with high-level interfaces to common compiler toolsets like
  MSVC, Clang, GCC, Java, Protobuf, Yacc, Cython, Flex, NVCC
* **Consequent** out-of-tree builds

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
scripts. There are two ways a Craftr module can be created:

1. A file named ``Craftfile.py`` with a ``# craftr_module(...)`` declaration
2. A file named ``craftr.ext.<module_name>.py``

By default, Craftr will execute the ``Craftfile.py`` from the current
working directy if no different main module is specified with the ``-m``
option. Below you can find a simple Craftfile that can build a C++ program
on any platform (that is supported by the Craftr STL).

.. code-block:: python

  # craftr_module(my_project)

  from craftr import path                   # similar to os.path with a lot of additional features
  from craftr.ext.platform import cxx, ld   # import the C++ compiler and Linker for the current platform

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

To get you an idea of what's going on, we pass the `-v` flag to enable
more detailed output. What you see below is an example run on Windows:

::

  λ craftr -ev
  detected ninja v1.6.0
  $ cd "build"
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

To install from the Git repository, use the `-e` flag to be able to update
Craftr by simply pulling the latest changes from the remote repository.

::

    git clone https://github.com/craftr-build/craftr.git && cd craftr
    pip install -e .

Targets
-------

Craftr describes builds with :class:`Targets<craftr.Target>`. Each
Target has a list of input and output files and a command line to create
the output files. It is the most basic class and in many cases, it is not
needed to use it directly. If however you have very fixed requirements,
you can still use it and hard-code the command line.

.. code-block:: python

  # craftr_module(example)
  from craftr import *
  main = Target(
    command = 'gcc $in -o $out',
    inputs = path.local(['src/main.c', 'src/util.c']),
    outputs = 'main'
  )

This creates a Target called ``example.main`` that you can now export and
execute with `Ninja`_. Note that you can use the full target specifier that
was mentioned before or a relative target specified like ``.main``.

::

  $ craftr -eb .main
  [1/1] gcc /home/niklas/Desktop/example/src/main....til.c -o /home/niklas/Desktop/example/build/main


Rules
-----

Most of the time, you will be using "rule functions" instead of the Target
class. Rule functions are basically just Python functions that build a Target
for you, sparing your the hazzle of generating the appropriate command-line
parameters. Rules usually use of the :class:`craftr.TargetBuilder` class to
make things easier.

.. code-block:: python

  # craftr_module(example)
  from craftr import *

  # An example rule function for GCC.
  def gcc(inputs, output, shared = False, debug = False, frameworks = (), **kwargs):
    builder = TargetBuilder(inputs, frameworks, kwargs)
    include = builder.merge('include')
    defines = builder.merge('defines')

    command = ['gcc', '$in', '-o', '$out']
    if shared:
      command += ['-shared', '-fPIC']
    if debug:
      command += ['-g', '-O0']
    else:
      command += ['-O2']
    command += ['-I' + i for i in include]
    command += ['-D' + d for d in defines]

    return builder.create_target(command, outputs = [output])

  main = gcc(
    output = 'main'
    inputs = path.local(['src/main.c', 'src/util.c']),
    shared = False,
    include = path.local(['include']),
    defines = ['COOL_KIDS'],
  )

The :class:`~craftr.TargetBuilder` does a lot of things for us:

* Expand the list of ``inputs`` using :func:`craftr.expand_inputs` (in case
  of :class:`~craftr.Target` objects being passed, this will automatically
  add frameworks used by that target to the framework list)
* Create a proxy :class:`~craftr.Framework` for the specified ``**kwargs``
* Create a :class:`~craftr.FrameworkJoin` from the frameworks list so we
  can do things like joining all lists of ``includes`` and ``defines`` into
  a single list
* Check for unused options directly passed to the rule via ``**kwargs`` in
  :meth:`~craftr.TargetBuilder.create_target` and eventually yield a warning

There are a bunch of rules provided by the built-in Craftr extension modules
to compile C/C++, C#, Java, etc. For example, the ``ext.platform`` Craftr module
gives you access to a compiler implementation for C/C++. These are based on
``compiler.gcc``, ``compiler.clang`` or ``compiler.msvc`` based on your platform
and environment. Go to :ref:`compiler_abstraction` for more information.

Frameworks
----------

The :class:`craftr.Framework` is in fact just a dictionary (with an
additional :attr:`name<craftr.Framework>` attribute) that represents
a set of options for anything build related. How the data in a framework
is interpreted depends on the rule that interprets it.

The easiest way to use frameworks and to demonstrate their usefulness
is with the Craftr module for a very simple C++ library, in this case
the header-only `nr_matrix`_ library.

.. code-block:: python

    # craftr_module(libs.nr_matrix)

    from craftr import Framework, path
    from craftr.ext.libs.nr_iterator import nr_iterator

    nr_matrix = Framework(
      include = [path.local('include')],
      frameworks = [nr_iterator],
    )

Rule functions like the ``compile()`` methods of the C++ compiler
implementations will usually accumulate all ``include`` values to
generate a list of include paths, the same for the ``defines`` etc.

Frameworks are usually passed to a rule function with the ``frameworks``
keyword parameter, however there are additional places where they could
be coming from.

1. Nested frameworks: As you can see above, the ``nr_matrix`` framework
   specifies ``nr_iterator`` as an additional required framework
2. Target frameworks: All the frameworks that were used to generate a
   target are transfered to the :attr:`craftr.Target.frameworks`
   attribute and are taken into consideration when passing a target as
   input to rule functions, eg:

   .. code-block:: python

      from craftr.ext.platform import cxx, ld
      from craftr.ext.libs.some_cool_library import some_cool_library  # a Framework

      obj = cxx.compile(
        sources = path.glob('src/*.cpp'),
        frameworks = [some_cool_library],
        std = 'c++11',
      )

      bin = ld.link(
        output = 'main',
        inputs = obj,    # Here, the frameworks that were used for "obj" will
                         # automatically be passed on to the link() rule
      )

Tasks
-----

Craftr allows you to embedd arbitrary Python procedures into the Ninja
manifest and thus the dependency graph and build process with the
:func:`craftr.task` decorator.

For more information, see :doc:`rts`.

Command Line Interface
----------------------

.. note:: Craftr exports `Ninja`_ build definitions but also acts as a wrapper
  for calling it. While you can just export the Ninja manifest and run invoke
  ``ninja`` manually, it is usually much more convenient to do so through
  Craftr.

::

  craftr [-h] [-V] [-v] [-m MODULE] [-n] [-e] [-b] [-c]
         [-d PATH] [-p PATH] [-D <key>[=<value>]] [-I PATH]
         [-N ...] [--no-rc] [--rc PYFILE] [--strace-depth INT]
         [--rts] [--rts-at HOST:PORT]
         [targets [targets ...]]

  Craftr v1.1.0-dev
  -----------------

  Craftr is the next generation build system based on Ninja and Python.

  https://github.com/craftr-build/craftr

  positional arguments:
    targets               zero or more target/task names to build/execute

  optional arguments:
    -h, --help            show this help message and exit
    -V, --version         print version and exit (1.1.0-dev)
    -v, --verbose         increase the verbosity level
    -m MODULE, --module MODULE
                          name of the main Craftr module to take relative target
                          references for or the module to load if no targets are
                          specified on the command-line
    -n, --no-build        skip the build step
    -e, --export          (re-)export the Ninja manifest
    -b                    deprecated since v1.1.0
    -c, --clean           clean the specified target(s), specify twice for
                          recursive clean
    -d PATH, --build-dir PATH
                          build directory, defaults to "./build" or the cwd if
                          -p is used (conflicts with -p)
    -p PATH, --project-dir PATH
                          inverse of -b, use the specified directory as the main
                          project directory and the cwd for -b
    -D <key>[=<value>], --define <key>[=<value>]
                          set an option in the environment variable, <key> may
                          be relative, =<value> can be omitted
    -I PATH, --search-path PATH
                          additional Craftr module search path
    -N ..., --ninja-args ...
                          additional args passed to the Ninja command-line
    --no-rc               skip running craftrc.py files
    --rc PYFILE           run the specified Python file before anything else,
                          CAN be paired with --no-rc
    --strace-depth INT    depth of the logging stacktrace, default is 5
    --rts                 keep alive the runtime server
    --rts-at HOST:PORT    override the runtime server's host:port

.. note::

  Craftr will try to skip the phase of executing the Craftfile if possible.
  For example, if you only use the ``-b`` option to invoke Ninja, Craftr
  will inform you that the execution phase is skipped.

  Also, to ensure consistency of the environment variables when building
  with Craftr, options that are specified with the ``-D`` option are written
  into the Ninja manifest. If ``-e`` is *not* passed, Craftr will read these
  cached options and *prepend* them to the list of ``-D`` options.

  ::

    $ craftr -e -Ddebug
    $ craftr -b
    craftr: [INFO ]: skipping execution phase.
    craftr: [INFO ]: prepending cached options: -Ddebug


Target References & Build Options
---------------------------------

You can pass absolute or relative target names to Craftr and it will then use
these targets where applicable. For example ``craftr -b .lib`` will build the
lib target from your Craftfile. An absolute target name does *not* begin with
a dot.

Options are set via environment variables. This is the order in which the
variables are overwritten:

1. Envrionment variables from your shell
2. ``craftrc.py`` files that modify the :data:`craftr.environ` dictionary
3. The ``-D`` option that can be specified on the command-line
4. Craftr modules that modify the :data:`craftr.environ` dictionary

Note that you can pass relative identifiers to the ``-D`` option as well.
If your Craftfile identifier is ``my_project`` and you pass
``craftr -D.debug=true``, it will set the environment variable
``my_project.debug`` to the string ``true``.

.. note::

  You can also reference targets from a Craftr module that would normally
  not be imported into your current Craftfile. For instance, lets say you
  have a library called `libs.myfoo` and the build definitions are in a
  ``Craftfile.py`` and you have a `libs.myfoo.test.craftr` file that exposes
  a ``run`` target, you can do this from the command-line:

  ::

    craftr -eb .test.run

  Instead of having to switch the main module.

  ::

    craftr -m libs.myfoo.test -eb .run


craftrc.py Files
-----------------

Before Craftr will execute the main Craftr module, it will look for ``craftrc.py``
files in the user home and working directory and execute them. It will skip
this step if you pass ``--no-rc``. You can specify a difference file instead
of the ``craftrc.py`` of the current working directory with the ``--rc <filename>``
option.

Craftr RC files are intended to setup environment variables that can have
influence on the build process on a per-user and per-project basis. The RC files
are execute **before** the options passed with ``-D`` are set.

For example, for using the `craftr.ext.qt5`_ module on Windows, I use this
``craftrc.py`` file in my home directory:

.. code-block:: python

  from os import environ
  if 'Qt5Path' not in environ:
    environ['Q5Path'] = 'D:\\lib\\Qt\\5.5\\msvc2013_64'

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

The Craftr meta build system
============================

Craftr is a cross-platform meta build system based on `Ninja`_. To whet your
appetite, here's a simple ``Craftfile`` to build a C++ program:

.. code-block:: python

  # craftr_module(simple)
  from craftr import *
  from craftr.ext.platform import cxx, ld

  obj = cxx.compile(
    sources = path.glob('src/*.cpp')
  )
  program = ld.link(
    inputs = obj
  )

**Key Features** of Craftr:

- Modular builds written in Python
- Integrate `Tasks`_ that can be invoked from the command-line
- Easily extensible framework
- Builtin support for C/C++ (MSVC, GCC, LLVM), Java, C#, Flex, Yacc and ProtoBuf
- **[todo]** Cross-platform support for OpenCL, CUDA, Vala

**Requirements**:

- `Ninja`_
- `Python`_ 3.4 or newer

**Contents**:

.. toctree::
  :maxdepth: 1

  self
  ext
  api
  compiler_abstraction
  rts
  magic

Installation
------------

You should install Craftr using `Pip`_, preferably into a `virtualenv`_. Craftr
is currently an alpha project in active development and changes very quickly.
It is therefore recommended to use an *editable Pip installation* from the
cloned Git repository.

::

  $ git clone git@github.com:craftr-build/craftr.git
  $ cd craftr
  $ pip install -e .

You can grab the latest version of Craftr by doing

::

  $ git pull origin master
  $ pip install -e .

Getting Started
---------------

There is usually a file named "Craftfile" in your current working directory.
This file is a Python script that will be executed when you run ``craftr``.
Every Craftfile must have a module name declaration in its head. It can be
anywhere in the first comment-block of the file.

.. code-block:: python

  # -*- mode: python; -*-
  # Copyright (C) 2016  Niklas Rosenstein
  # craftr_module(my_module_name)
  print("Hello Craftr! This is", project_name)

To run this script, simply type ``craftr`` in your command-line.

::

  $ craftr
  Hello Craftr! This is my_module_name
  $ ls
  Craftfile build

.. note:: You can also explicitly specify the name of the Craftr module
  to execute by using the ``-m`` option like ``craftr -m my_module_name``
  (see `Command Line Interface`_ for more information).

.. _BuildDirSwitch:

You might have noticed that ``build`` directory that appeared in your
current working directory all of the sudden. Craftr always switches to
the build directory before executing modules and exporting a Ninja manifest,
thus the build directory must exist before anything else can happen. The
default build directory is called "build" and you can change it with the
``-d`` or ``-p`` command line options.

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
execute with `Ninja`_.

::

  $ craftr -eb .main
  [1/1] gcc /home/niklas/Desktop/example/src/main....til.c -o /home/niklas/Desktop/example/build/main

.. note:: The ``.main`` argument is a relative target reference. You can also
  pass the full target name ``example.main`` instead or just omitt the argument
  completely if you want to build just everything.

  Also, :ref:`Craftr always switches to the build directory<BuildDirSwitch>`,
  which is why we use the :func:`path.local()<craftr.path.local>` function to
  create a path relative to the "Craftfile" directory.

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
and environment. Go to :doc:`compiler_abstraction` for more information.

Frameworks
----------

.. todo::


Tasks
-----

You can run any Python function of a Craftr module from the command-line
with the ``-f`` (before build) and/or ``-F`` (after build) option. A simple
example is a function to upload a build product to a server.

.. code-block:: python

  # -*- mode: python; -*-
  # craftr_module(awesome.app)

  from craftr import *
  from craftr.ext.archive import Archive
  from craftr.ext.git import Git
  from craftr.ext.platform import cxx, ld

  objects = cxx.compile(sources = path.glob('src/*.c'))
  program = ld.link(output = 'main', inputs = objects)

  def upload():
    info('creating archive ...')
    git = Git(project_dir)
    archive = Archive(prefix = '{0}-{1}'.format(project_name, git.describe()))
    archive.add('res')
    archive.add(program.outputs, parts = 1)
    archive.save()

    info('uploading ...')
    shell.run(['scp', archive.name, 'my-host:./uploads'], check=True)

This can now be run with ``craftr -ebF upload``. You can omit the ``-e`` and
``-b`` option if you don't need them!

Command Line Interface
----------------------

.. note:: Craftr exports `Ninja`_ build definitions but also acts as a wrapper
  for calling it. While you can just export the Ninja manifest and run invoke
  ``ninja`` manually, it is usually much more convenient to do so through
  Craftr.

::

  $ craftr -h
  usage: craftr.py [-h] [-V] [-v] [-m M] [-e] [-b] [-c] [-d D] [-p P] [-D D]
                   [-f F [F ...]] [-F F [F ...]] [-N ...] [--no-rc] [--rc RC]
                   [--strace-depth STRACE_DEPTH] [--rts] [--rts-at RTS_AT]
                   [targets [targets ...]]

  positional arguments:
    targets

  optional arguments:
    -h, --help            show this help message and exit
    -V                    Print version and exit.
    -v                    Increase the verbosity level.
    -m M                  The name of a Craftr module to run.
    -e                    Export the build definitions to build.ninja
    -b                    Build all or the specified targets. Note that no
                          Craftr modules are executed, if that is not required
                          by other options.
    -c                    Clean the targets before building. Clean recursively
                          on -cc
    -d D                  The build directory. Defaults to "build". Can be out
                          of tree.
    -p P                  Specify the main directory (eventually to load the
                          Craftfile from). If -d is not specified, the CWD is
                          build directory.
    -D D                  Set an option (environment variable). -D<key> will set
                          <key> to the string "true". -D<key>= will delete the
                          variable, if present. -D<key>=<value> will set the
                          variable <key> to the string <value>. <key> can be
                          prefixed with a dot, in which case it is prefixed with
                          the current main modules name.
    -f F [F ...]          The name of a function to execute.
    -F F [F ...]          The name of a function to execute, AFTER the build
                          process if any.
    -N ...                Additional args to pass to ninja
    --no-rc               Do not run Craftr startup files.
    --rc RC               Execute the specified Craftr startup file. CAN be
                          paired with --no-rc
    --strace-depth STRACE_DEPTH
                          Depth of logging stack trace. Defaults to 3
    --rts                 If this option is specified, the Craftr runtime server
                          will serve forever.
    --rts-at RTS_AT       Manually specify the host:port for the Craftr runtime
                          server.

Target References & Build Options
---------------------------------

You can pass absolute or relative target names to Craftr and it will then use
these targets where applicable. For example ``craftr -b .lib`` will build the
lib target from your Craftfile. An absolute target name does *not* begin with
a dot.

Options are set via environment variables. This is the order in which the
variables are overwritten:

1. Envrionment variables from your shell
2. ``.craftrc`` files that modify the :data:`craftr.environ` dictionary
3. The ``-D`` option that can be specified on the command-line
4. Craftr modules that modify the :data:`craftr.environ` dictionary

Note that you can pass relative identifiers to the ``-D`` option as well.
If your Craftfile identifier is ``my_project`` and you pass
``craftr -D.debug=true``, it will set the environment variable
``my_project.debug`` to the string ``true``.


.craftrc Files
--------------

Before Craftr will execute the main Craftr module, it will look for ``.craftrc``
files in the user home and working directory and execute them. It will skip
this step if you pass ``--no-rc``. You can specify a difference file instead
of the ``.craftrc`` of the current working directory with the ``--rc <filename>``
option.

Craftr RC files are intended to setup environment variables that can have
influence on the build process on a per-user and per-project basis. The RC files
are execute **before** the options passed with ``-D`` are set.

For example, for using the `craftr.ext.qt5`_ module on Windows, I use this
``.craftrc`` file in my home directory:

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

You can use the ``pdb`` module for an interactive debugging session in your
Craftr script if anything doesn't work as you would expect it to. Simply put
the following line at the position you want the program to be paused for
debugging.

.. code-block:: python

  import pdb; pdb.set_trace()

You can also enable verbose output that will enable a stack trace being printed
with every line of log message that is being output by Craftr modules. The stack
trace is stripped to one line per frame and limited to 5 frames. If you specify
``-v``, the traceback will only be printed for :func:`craftr.error` calls. If
you want to enable it for :func:`craftr.info` and :func:`craftr.warn` as well, use
``-vv``. You can also specify the ``--strace-depth`` option to specify the depth
of the stack trace.

.. image:: http://i.imgur.com/IQL5GzN.png


.. image:: http://i.imgur.com/VcyF801.png


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

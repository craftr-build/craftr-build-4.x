Command-line interface
======================

Craftr's command-line interface should feel easy, quick
and efficient to use. There are only flags that alter
the manifest export and build process and no subcommands.

Synopsis
--------

::

    usage: craftr [-h] [-V] [-v] [-m MODULE] [-b] [-e] [-c] [-d PATH] [-p PATH]
                  [-D <key>[=<value>]] [-I PATH] [-N ...] [-t {standard,external}]
                  [--no-rc] [--rc FILE] [--strace-depth INT] [--rts]
                  [--rts-at HOST:PORT]
                  [targets [targets ...]]

    https://github.com/craftr-build/craftr

    positional arguments:
      targets

    optional arguments:
      -h, --help            show this help message and exit
      -V, --version
      -v, --verbose
      -m MODULE, --module MODULE
      -b, --skip-build
      -e, --skip-export
      -c, --clean
      -d PATH, --build-dir PATH
      -p PATH, --project-dir PATH
      -D <key>[=<value>], --define <key>[=<value>]
      -I PATH, --search-path PATH
      -N ..., --ninja-args ...
      -t {standard,external}, --buildtype {standard,external}
      --no-rc
      --rc FILE
      --strace-depth INT
      --rts
      --rts-at HOST:PORT

``targets``
-----------

Zero or more targets to build. Target names can be absolute or relative
to the main module name (beginning with a period). Targets that are
referenced from modules that haven't been imported already will be imported.

If the specified target or targets are only Python backed tasks (see
:func:`craftr.task`), Ninja will **not** be invoked since the tasks
can be executed solely on the Python side. In many cases, this is
often even desired (eg. if you're using Craftr only for tasks).

``-V, --version``
-----------------

Display the version of Craftr and exit immediately.

``-v, --verbose``
-----------------

Add to the verbosity level of the output. This flag can
be specified mutliple times. Passing the flag once will
enable debug output and show module name and line number
on logging from Craftr modules. Also, stracktraces are
printed for :func:`craftr.error` uses in Craftr modules.

A verbosity level of two will enable stacktraces also for
logging calls with :func:`craftr.info` and :func:`craftr.warn`.

This flag will also cause ``-v`` to be passed to subsequent
invokations of Ninja.

``-m, --module``
----------------

Specify the main Craftr module that is initially loaded.
If not specified, the Craftfile in the current working
directory is loaded.

.. _no_build:

``-b, --skip-build``
--------------------

Skip the build phase.

``-e, --skip-export``
---------------------

Skip the export phase and, if possible, even the step of
executing Craftr modules. If ``-n, --no-build`` is not passed,
ie. building should take place, a previous invocation must
have exported the Ninja build manifest before, otherwise
the build can not execute.

If a manifest is present, Craftr loads the original search
path (``-I``) and options (``-D``), so you don't have to
specify it on the command-line again! Craftr will act like
a pure wrapper for Ninja in this case.

Note that in cases where tasks are used and required for
the build step, Craftr can not skip the execution phase.

*Changed in v1.1.0*: Inverted behaviour.

``-c, --clean``
---------------

Clean the specified targets. Pass the flag twice to clean
recursively which even works without explicitly specifying
a target to clean.

``-d, --build-dir``
-------------------

Specify the build directory. Craftr will automatically
switch to this directory before the main module is exeucted
and will stay inside it until the build is completed.

``-p, --project-dir``
---------------------

Similar to ``-d, --build-dir``, but this option will cause
Craftr to use the current working directory as build directory
and instead load the main module from the specified project
directory.

``-D, --define``
----------------

Format: ``-D key[=value]``

Set an option, optionally with a specific string value.
This option is set in the environment variables of the
Craftr process and inherit by Ninja. The ``key`` may be
anything, but if it begins with a period, it will be
automatically prefixed with the main module identifier.

As an example, say the Craftfile in your working directory
has the identifier ``my_module``. Using ``-D.debug=yes``
will set the environment variable ``my_module.debug`` to
the string ``'yes'``.

If you leave out the value part, the option is set to the
string value ``'true'``. If you keep the assignment operator
without value, the option will be *unset*.

``-I, --search-path``
---------------------

Add an additional search path for Craftr modules.

``-N, --ninja-args``
--------------------

Consumes all arguments after it and passes it to the Ninja
command in the build step.

``-t, --buildtype {standard, external}``
----------------------------------------

Switch between standard or externally controlled build. Choosing
the ``external`` option will cause target generator functions to
consider environment variables like ``CFLAGS``, ``CPPFLAGS``,
``LDFLAGS`` and ``LDLIBS`` or whatever else is applicable to the
target generator you're using.

.. note:: The consideration of these environment variables is
          completely dependent on the implementation of the
          target generator.

.. seealso:: The selected buildtype can be read from the
             :attr:`craftr.Session.buildtype` attribute.

``--no-rc``
-----------

Don't run ``craftrc.py`` files

``--rc``
--------

Specify a file that will be executed before anything else. It will
be executed the same way ``craftrc.py`` files are. Can be combined
with ``--no-rc`` to exclusively run the specified file.

``--strace-depth``
------------------

Specify the depth of the stacktrace when it is printed. This is only
for stacktraces printed with the :ref:`logging_funcs`. The default
value is 5. Also note that frames of builtin modules are hidden from
this stacktrace.

``--rts``
---------

Keep alive the Craftr runtime server until you quit it with CTRL+C.

``--rts-at``
------------

Specify the ``HOST:PORT`` for the Craftr runtime server instead of
picking loopback and a random port.

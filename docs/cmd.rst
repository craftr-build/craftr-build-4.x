Command-line interface
======================

Craftr's command-line interface should feel easy, quick
and efficient to use. There are only flags that alter
the manifest export and build process and no subcommands.

.. contents::

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

``-n, --no-build``
------------------

Skip the build phase.

``-e, --no-export``
-------------------

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

``-b, --build-dir``
-------------------

Specify the build directory. Craftr will automatically
switch to this directory before the main module is exeucted
and will stay inside it until the build is completed.

``-p, --project-dir``
---------------------

Similar to ``-b, --build-dir``, but this option will cause
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
the string ``'yes''`.

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

``--buildtype``
---------------

Choices: ``standard``, ``external``

Choose the buildtype. This option does not necessarily have
any influence on the build, it must be respected by the
Craftfile and/or rule functions used.

The default value for this argument is ``standard``. Choosing
``external`` will cause rules that implement it to take external
options into account, like ``CFLAGS``, ``CPPFLAGS`` and ``LDFLAGS``.

See: :attr:`craftr.Session.buildtype`

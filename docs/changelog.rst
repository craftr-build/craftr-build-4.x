Changelog
=========

v1.1.1
------

* Behaviour changes

  * add ``__no_default`` target when there are no default targets, printing
    "no default target"
  * removed default ``clean`` target, use ``-c`` or ``-cc`` command-line option
  * catching :class:`craftr.ModuleError` no longer prints the error text (#118)

* API related changes

  * add ``frame`` and ``module`` argument to :func:`craftr.log`
  * add :func:`Target.as_explicit`
  * add :data:`craftr.ext.platform.asm` compiler proxy
  * :func:`craftr.memoize_tool` will be deprecated in the future and is now
    a synonym for :func:`functools.lru_cache`
  * :func:`craftr.shell.run()` now manually checks if the program exists and
    raises a :class:`FileNotFoundError` exception if it does not (only if
    ``shell=True``)
  * add :func:`craftr.utils.override_environ`
  * add :func:`craftr.ext.rules.alias` function

* C/C++ related changes

  * C/C++ compiler implementations now take ``debug`` option into account if
    no explicit value is passed to the generator function

* Cython related changes

  * add :doc:`Cython tutorial<tutorials/cython>` to docs
  * Cython compiler program can now be overwritten with ``CYTHONC``
  * add :class:`craftr.ext.compiler.cython.PythonInfo` class
  * add :func:`craftr.ext.compiler.cython.CythonCompiler.compile_project` method

v1.1.0
------

* NEW: Tasks (replaces ``craftr.ext.rules.PythonTool``)

  * created with the new ``task()`` function/decorator
  * can be specified on the command-line
  * exported to the Ninja manifest
  * run through Craftr RTS

* huge file naming scheme changes (issue #95)

  * rename ``Craftfile`` to ``Craftfile.py``
  * rename ``.craftrc`` to ``craftrc.py``
  * rename ``<some_module>.craftr`` to ``craftr.ext.<some_module>.py``

* Standard Library

  * remove ``craftr.ext.options`` module, use ``craftr.options`` instead (issue #97)
  * add support for ``msvc_runtime_library_option`` which can have the
    value ``'dynamic'`` or ``'static'``
  * remove ``craftr.ext.rules.PythonTool`` and rewrite ``~.render_template()``
  * update ``compiler.cython`` documentation
  * fix missing ``foreach=True`` in ``CythonCompiler.compile()``
  * add :mod:`craftr.ext.python` module
  * fix ``-shared`` argument to LLVM/GCC ``.link()`` rule (fix #109)
  * MSVC C++ compiler is now read from ``CXX`` variable instead of ``CC``
  * Linux linker is now read from ``CC`` variable instead of ``CCLD``
  * support for ``CFLAGS``, ``CPPFLAGS``, ``ASMFLAGS``, ``LDFLAGS`` and
    ``LDLIBS`` (see issue #111)
  * Add ``craftr.ext.cmake`` module (issue #113)

* General

  * ``setup.py`` now uses ``entry_points`` to install console scripts (issue #94)

* Behaviour changes

  * automatically import targets specified on the command-line (issue #96)
  * catch possible PermissionError in ``CraftrImporter._rebuild_cache()``
    (sha 16a6e307)
  * module and session context is now available when a task is executed (issue #99)
  * fix ``TargetBuilder.write_command_file()``, now correctly returns the
    filename even if no file is actually created
  * sophisticated target check on build-only invokation if RTS is required
    (and thus the execution step can not be skipped) (issue #98)
  * new Craftr data caching method using JSON in the Ninja build manifest
    (also fixes #100) (issue #101)
  * Craftr RTS now works with task-targets, removed ``MSG_ARGUMENT``
    and ``_RequestHandler.arglist``
  * functions wrapped with the ``task()`` decorator can now be specified
    on the command-line just like normal targets (due to the fact that
    they are real targets also exported to the Ninja manifest)
  * if all targets specified on the command-line are tasks and do not
    depend on Ninja-buildable targets, the task(s) will be executed
    without Ninja (issue #103)
  * if ``-e`` is not specified but the manifest does not exist, export
    will be forced unless the specified targets do not require it (ie.
    are plain tasks) (see #103)
  * calling ``Session.update()`` after altering ``Session.path`` is
    no longer necessary (issue #108)

* Command-line changes

  * inverted behaviour of ``-e``!! Now causes skip of
    the export and eventually execution step (if possible), short
    version of ``--skip-export``
  * inverted behaviour of ``-b``!! Now causes skip of
    the build phase, short version for ``--skip-build``
  * removed ``-f`` and ``-F`` command-line options completely (instead,
    tasks that do not depend on normal targets can be executed without
    Ninja, see #103)
  * deprecated ``-b`` flag, the build step is now always executed by default
  * add ``-n`` flag which is the inverse of the old ``-b`` flag, skip the
    build phase if specified
  * updated command help
  * passing ``-v`` will automatically add ``-v`` to the Ninja invokation
  * add ``--buildtype`` option for which you can choose to pass the value
    ``standard`` (default) or ``external``

* API Changes

  * add ``task()`` decorator function
  * add ``TaskError`` exception class
  * ``TargetBuilder()`` now accepts None for its *inputs* parameter
  * ``TargetBuilder()`` now has default values for the *frameworks* and
    *kwargs* parameters
  * removed ``options.get_option()``
  * ``options.get()`` now accepts a *default* parameter, updated its docstrings
  * passing ``NotImplemented`` for *default* to ``options.get()`` now raises
    a ``KeyError`` if the option does not exist
  * add ``option.get_bool()``

  * removed ``Session.update()`` (see issue #108)
  * removed ``Session.rts_funcs``
  * add ``Session.files_to_targets``
  * add ``Session.finalized``
  * add ``Session.finalize()``
  * add ``Session.find_target_for_file()``
  * add ``Session.buildtype``

  * add ``Target.rts_func``
  * add ``Target.requires``
  * add ``Target.graph``
  * add ``Target.finalize``
  * add ``Target.finalized`` property
  * add ``Target.get_rts_mode()``
  * add ``Target.execute_task()``
  * Targets can now also be tasks which will be executed through Craftr
    RTS by passing a callable to the constructor for the *command* argument
    (you should prefer the ``task()`` function though)

  * add ``craftr.path.buildlocal()`` function
  * add ``craftr.shell.format()`` and ``~.join()`` functions
  * ``craftr.shell.run()`` now splits strings into a command list if
    the *shell* argument is False

* Logging

  * removed the ``craftr: [INFO ]:`` prefix stuff
  * logging functions only display the source module when at least ``-v``
    is specified
  * updated output coloring and debug message strings
  * stracktrace for log entries now skips builtin modules

v1.0.0
------

* initial release version

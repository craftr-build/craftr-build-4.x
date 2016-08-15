Changelog
=========

v1.1.2
------

* Bug fixes

  * Fixed target name deduction with chained function calls on
    generator functions (#122)
  * MSVC fixed handling of keep_suffix and force_suffix options
  * MSVC compiler now correctly deduces a correct compiler version
    if multiple versions are specified and the first can not be used

* Behaviour changes

  * If the folders ``./craftr/`` and ``./craftr/modules`` exist in the
    project directory, they will automatically be added to the Craftr
    search path
  * The ``Craftfile.py`` is now also searched for not only in the current
    working directory but also in the ``craftr/`` directory

* API Changes

  * Removed ``craftr.memoize_tool()`` function which was deprecated in v1.1.1
  * Removed ``craftr.options`` module! (some backwards compatibility maintained
    by new ``options`` object in module globals, see below)
  * Added new ``options`` built-in for Craftr modules (of type
    :class:`craftr.ModuleOptionsNamespace`) that serves as a namespace for
    option values declared in the ``__options__`` builtin
  * Added new ``__options__`` built-in (of type :class:`craftr.ModuleOptions`)
    that should be used to declare module options, eg:

    .. code:: python

      # craftr_module(my_module)
      __options__.add('staticbuild', type=bool)
      info(options.debug)
      info(options.staticbuild)

  * Added :attr:`craftr.Session.options` (of type :class:`craftr.ModuleOptions`)
    that contains options that are globally inherited by all Craftr modules
  * Removed ``craftr.magic.get_caller()``
  * All module-level options can now be read from the unprefixed version
  * :class:`craftr.TargetBuilder` now has a ``caller_options`` member
    that contains the ``__options__`` variable of the frame that created
    the ``TargetBuilder``
  * :meth:`craftr.TargetBuilder.get` now also reads options of the module
    that created the ``TargetBuilder``

* Compiler changes

  * MSVC version detection now detects include errors and raises a
    :craftr:`~craftr.ext.compiler.ToolDetectionError` in that case (can
    happen with an incomplete VS installation)
  * Support new ``rtti`` option in LLVM and MSVC compiler

v1.1.1
------

* Bug fixes

  * Logging in Craftr RTS fails with Runtime Error (#104)
  * Fix wrong target name deduction with chained function calls on
    target generator functions (#122)

* Behaviour changes

  * add ``__no_default`` target when there are no default targets, printing
    "no default target"
  * removed default ``clean`` target, use ``-c`` or ``-cc`` command-line option
  * catching :class:`craftr.ModuleError` no longer prints the error text (#118)
  * :func:`craftr.TargetBuilder.get` now resolves options in a new order:

    1. ``kwargs`` passed to the constructor (highest priority)
    2. Environment options (read using :func:`options.get`)
    3. Options from the frameworks (read using :class:`craftr.FrameworkJoin`)

  * ``normpath()`` no longer lowers paths on windows (#92)
  * add support for iterables other than strings in :func:`path.basename`,
    :func:`path.dirname` and :func:`path.split`
  * renamed ``path.split_path()`` to :func:`path.split_parts`

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
  * add :meth:`craftr.TargetBuilder.mkname` method
  * add :func:`craftr.TargetBuilder.setdefault` method
  * add :data:`craftr.FrameworkJoin.defaults` member
  * add :func:`craftr.FrameworkJoin.iter_frameworks` method
  * moved ``craftr.ext.compiler.BaseCompiler`` to :class:`craftr.ext.compiler.base.BaseCompiler`,
    backwards compatible import exists
  * removed ``BaseCompiler.__getitem__()`` and ``~.__setitem__()``
  * add ``BaseCompiler.register_hook()``
  * :meth:`craftr.TargetBuilder.add_framework()` was updated
  * replace ``craftr.utils.slotobject()`` with :func:`~craftr.utils.recordclass`
    (alias introduced for backwards compatibility)
  * :mod:`craftr.utils` is now a package, some name changes but backwards
    compatibility has been kept by introducing aliases
  * fix :class:`~craftr.magic.Proxy` ``__name__`` attribute always
    returning :const:`None` instead of the underlying object's member value
  * fix :func:`craftr.path.buildlocal` now using ``project_name`` instead
    of ``__name__``
  * :data:`~craftr.ext.platform.cc`, :data:`~craftr.ext.platform.cxx`,
    :data:`~craftr.ext.platform.ld` etc. are no longer proxies but real
    objects
  * add :func:`craftr.ext.rules.run` ``requires`` parameter
  * add :func:`craftr.utils.keep_module_context` function
  * removed ``craftr.FrameworkJoin.used_keys`` and added
    :attr:`craftr.TargetBuilder.used_options` instead
  * add :func:`craftr.path.projectlocal`
  * :func:`craftr.ext.compiler.gen_objects` now determines the base directory
    of the specified source files in a more meaningful way to avoid collisions
    with other invokations that could potentially generate the same filename
    when both invokations received files with the same basename in different
    folders
  * removed ``craftr.ext.compiler.gen_output_dir()``, use :func:`path.buildlocal` instead

* C/C++ related changes

  * C/C++ compiler implementations now take ``debug`` option into account if
    no explicit value is passed to the generator function
  * removed ``'clang'`` as a compiler name
  * added support for ``***_compile_remove_flags`` and ``***_link_remove_flags``
    options where ``***`` can be ``msvc``, ``llvm`` and ``gcc``
  * add support for ``msvc_runtime_library`` and ``force_include`` options
  * add support for ``link_target`` output variable
  * add ``force_suffix`` option to MSVC compiler

* Cython related changes

  * add :doc:`Cython tutorial<tutorials/cython>` to docs
  * Cython compiler program can now be overwritten with ``CYTHONC``
  * add support for ``embed`` parameter to :func:`~craftr.ext.compiler.cython.CythonCompiler.compile`
  * add :class:`~craftr.ext.compiler.cython.PythonInfo` class
  * add :func:`~craftr.ext.compiler.cython.CythonCompiler.compile_project` method

* :mod:`craftr.ext.cmake`

  * renamed ``render_config()`` to :func:`~craftr.ext.cmake.configure_file`
    to match the CMake naming and update parameter names

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

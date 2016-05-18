Changelog
=========

v1.1.0 (unreleased)
-------------------

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

  * deprecated ``craftr.ext.options`` module and moved it to ``craftr.options``,
    the module is now also automatically imported with ``from craftr import *``
    (issue #97)
  * add support for ``msvc_runtime_library_option`` which can have the
    value ``'dynamic'`` or ``'static'``
  * remove ``craftr.ext.rules.PythonTool`` and rewrite ``~.render_template()``

* General

  * ``setup.py`` now uses ``entry_points`` to install console scripts (issue #94)

* Behaviour changes

  * ``info()``, ``warn()`` and ``error()`` only display the module that
    called the function with a verbosity level ``> 0``
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

* Command-line changes

  * removed ``-f`` and ``-F`` command-line options completely (instead,
    tasks that do not depend on normal targets can be executed without
    Ninja, see #103)

* API Changes

  * add ``task()`` decorator function
  * add ``TaskError`` exception class

  * removed ``Session.rts_funcs``
  * add ``Session.files_to_targets``
  * add ``Session.finalized``
  * add ``Session.finalize()``
  * add ``Session.find_target_for_file()``

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

  * add ``craftr.shell.format()`` and ``~.join()`` functions
  * ``craftr.shell.run()`` now splits strings into a command list if
    the *shell* argument is False


v1.0.0
------

* initial release version

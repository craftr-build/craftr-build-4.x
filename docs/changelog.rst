Changelog
=========

v1.1.0 (unreleased)
-------------------

* huge file naming scheme changes (issue #95)

  * rename ``Craftfile`` to ``Craftfile.py``
  * rename ``.craftrc`` to ``craftrc.py``
  * rename ``<some_module>.craftr`` to ``craftr.ext.<some_module>.py``

* deprecated ``craftr.ext.options`` module and moved it to ``craftr.options``,
  the module is now also automatically imported with ``from craftr import *``
  (issue #97)
* automatically import targets specified on the command-line (issue #96)
* catch possible PermissionError in ``CraftrImporter._rebuild_cache()``
  (sha 16a6e307)
* fix ``TargetBuilder.write_command_file()``, now correctly returns the
  filename even if no file is actually created
* add support for ``msvc_runtime_library_option`` which can have the
  value ``'dynamic'`` or ``'static'``
* ``setup.py`` now uses ``entry_points`` to install console scripts (issue #94)
* add ``craftr.shell.format()`` and ``~.join()`` functions
* ``craftr.shell.run()`` now splits strings into a command list if
  the *shell* argument is False
* add ``Target.rts_func`` and constructor now accepts a callable for
  the *command* parameter
* removed ``Session.rts_funcs``
* add ``Session.has_rts_targets()``
* add ``task()`` decorator function
* Craftr RTS now searches in the registered targets for an RTS target
  and calls the RTS function with two arguments (inputs, outputs) instead
  of the arglist
* removed ``MSG_ARGUMENT`` from the Craftr RTS spec
* functions wrapped with the ``task()`` decorator can now be specified
  on the command-line just like normal targets
* remove ``craftr.ext.rules.PythonTool`` and rewrite ``~.render_template()``
  since they are no longer necessary with the new ``task()`` decorator
* add ``Target.execute_task()``
* module context is now available when a task is executed (issue #99)

v1.0.0
------

* initial release version

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

v1.0.0
------

* initial release version

API Documentation
=================

.. module:: craftr

This part of the documentation contains the API reference of the functions
and classes that can be used in Craftfiles.


Logging & Version Check
-----------------------

The logging functions implement the :func:`print` interface.

.. autofunction:: debug
.. autofunction:: info
.. autofunction:: warn
.. autofunction:: error
.. autofunction:: craftr_min_version

Tasks
-----

.. autofunction:: task

Helpers
-------

.. autofunction:: return_
.. autofunction:: expand_inputs
.. autofunction:: expand_frameworks
.. autofunction:: import_file
.. autofunction:: import_module

Session Objects
---------------

.. autoclass:: Session
  :members:

Target Objects
--------------

.. autoclass:: Target
  :members:

TargetBuilder Objects
---------------------

.. autoclass:: TargetBuilder
  :members:

Framework Objects
-----------------

.. autoclass:: Framework
  :members:

FrameworkJoin Objects
----------------------

.. autoclass:: FrameworkJoin
  :members:

The ``path`` module
-------------------

.. automodule:: craftr.path
  :members:

The ``shell`` module
--------------------

.. automodule:: craftr.shell
  :members:

The ``utils`` module
--------------------

.. automodule:: craftr.utils
  :members:

The ``options`` module
----------------------

.. automodule:: craftr.options
  :members:

.. autofunction:: craftr.options.get

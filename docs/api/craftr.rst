API Documentation
=================

.. module:: craftr

This part of the documentation contains the API reference of the functions
and classes that can be used in Craftfiles.

.. toctree::

  craftr.ext
  craftr.options
  craftr.path
  craftr.shell
  craftr.utils

.. autodata:: session
.. autodata:: module

.. _logging_funcs:

Logging
-------

The logging functions implement the :func:`print` interface.

.. autofunction:: debug
.. autofunction:: info
.. autofunction:: warn
.. autofunction:: error

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
.. autofunction:: craftr_min_version

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

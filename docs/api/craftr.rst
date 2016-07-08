API Documentation
=================

.. module:: craftr

This part of the documentation contains the API reference of the functions
and classes that can be used in Craftfiles.

.. toctree::
  :maxdepth: 1

  craftr.ext
  craftr.options
  craftr.path
  craftr.shell
  craftr.utils

.. data:: session

  A :class:`~craftr.magic.Proxy` to the current :class:`Session` object
  that is being used for the current Craftr build session.

  .. note::

    If you've used Flask before: It's similar to the Flask request object.

.. autodata:: module

  A :class:`~craftr.magic.Proxy` of the Craftr module that is currently
  being executed. Modules are standard Python module objects. When a
  Craftr extension module is being executed, this proxy points to exactly
  that module.

  .. code:: python

    # craftr_module(test)
    # A stupid example
    from craftr import module
    import sys
    assert project_name == module.project_name
    assert sys.modules[__name__] is module()

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

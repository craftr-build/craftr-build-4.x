Craftr Extension Modules
========================

Craftr comes with a set of builtin modules that contain useful functionality
to quickly write powerful Craftfiles. Most of the modules contain compiler
classes which in turn expose rule functions (ie. functions with a high level
interface that produce low-level targets). For more information on the
standard library, see :doc:`stl`.

A primer on Craftr modules
--------------------------

While Craftr modules can be imported from a Craftfile like any other
Python module, they are sligthly different in the file structure to make
them easier to use for common build scenarios. There are two ways to
create a Craftr module:

1. A ``Craftfile.py`` file with a ``#craftr_module(<module_name>)``
   declaration  at the top of the file
2. A ``craftr.ext.<module_name>.py`` file

While 2) is used more commonly for pure extension modules (eg. the whole
standard library of Craftr is built of those files), 1) is preferred for
the main build module of a project. There is no technical difference
between these two types of files though.

Importing Craftr Modules
------------------------

The :class:`craftr.Session` object manages a list of search paths for
Craftr modules. It is important to note that the Craftr modules in this
search path must **not** be directly inside the listed directories, but
they are additionally searched for one level deeper in the folder structure.

Consider the following project structure:

::

  my_project/
    Craftfile.py
    src/
    vendor/
      qt5/
        craftr.ext.qt5.py

In order to be able to import the Qt5 module, you only need to add the
``vendor/`` directory to the search path! This is a design decision that
was made for plain convenience.

.. code::

  #craftr_module(my_project)
  from craftr import *
  session.path.append(path.local('vendor'))
  from craftr.ext import qt5

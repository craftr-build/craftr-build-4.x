Extension Modules
=================

Actually, every Craftr module is an "extension module". Every Craftfile
can be imported from another Craftfile, given that it can be found by the
:class:`craftr.ext.CraftrImporter` (which searches in the :attr:`craftr.Session.path`
list). Extension modules can be imported from the ``craftr.ext`` package. Craftr
will look into the search path for a Craftfile with a ``# craftr_module(<name>)``
declaration or a ``<name>.craftr`` file (that does need such a declaration). Note
that it will also look in *all* first-level sub directories!

For example, your project structure might look like this:

::

  awesome.app/
    Craftfile
    src/
      ...
    vendor/
      qt5/
        qt5.craftr

To import the ``craftr.ext.qt5`` module, you first need to add ``vendor/``
to the :attr:`craftr.Session.path`. You can do this from a ``.craftrc`` file
or directly in your Craftfile. Note that you need to call the :func:`update()
<craftr.Session.update>` method, otherwise you still will not be able to
import the ``qt5`` module.

.. code-block:: python

  from craftr import *
  session.path.append(path.local('vendor'))
  session.update()

  from craftr.ext import qt5

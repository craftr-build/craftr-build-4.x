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

.. toctree::
  :maxdepth: 1

  self

Built-in Craftr extension modules
---------------------------------

.. toctree::
  :maxdepth: 2

  ext/archive
  ext/compiler
  ext/git
  ext/options
  ext/platform
  ext/rules
  ext/unix

Platform Abstraction Interface
------------------------------

.. todo::

.. _compiler_abstraction:

C/C++ Compiler Abstraction Interface
------------------------------------

This section only describes the interface for C/C++ compiler
implementations. Other compiler modules are described in their
respective module. See `Built-in Craftr extension modules`_. There are
implementations available for MSVC, LLVM and GCC (which currently inherits
the LLVM implementation).

Example:

.. code-block:: python

  # craftr_module(example)
  from craftr import *
  from craftr.ext.platform import cc, cxx, ld, ar

  some_library = ar.staticlib(
    inputs = cc.compile(
      sources = path.glob('some-library/*.c')
    )
  )

  objects = cxx.compile(
    sources = path.glob('src/*.cpp')
  )

  main = ld.link(
    inputs = [some_library, sources]
  )

  # You can read additional properties from the Target.meta dictionary
  info('static library path:', some_library.meta['staticlib_output'])
  info('main path:', some_library.meta['link_output'])

.. function:: cc.compile(source, frameworks=(), target_name=None, meta=None, **kwargs)
              cxx.compile(source, frameworks=(), target_name=None, meta=None, **kwargs)

  Compile the C/C++ *sources* into object files. The object files
  are generated using :func:`~craftr.ext.compiler.gen_objects`.

.. function:: ld.link(output, inputs, output_type='bin', frameworks=(), target_name=None, meta=None, **kwargs)

  Link the *inputs* into the file specified by *output*. The *output_type*
  defines whether an executable or shared library is created.

.. todo::

The Craftr standard library
===========================

Standard Library Modules
------------------------

.. toctree::
  :maxdepth: 1

  stl/archive
  stl/compiler
  stl/git
  stl/platform
  stl/python
  stl/rules
  stl/unix

.. _platform_interface:

Platform Interface
------------------

.. data:: platform.name

A string identifier of the platform. Currently implemented values are

* ``'win'``
* ``'cygwin'``
* ``'linux''``
* ``'darwin'``

.. data:: platform.standard

A string identifier of the platform standard. Currently implemented values are

* ``'nt'``
* ``'posix'``

.. function:: platform.obj(x)

Given a filename or list of filenames, replaces all suffixes with the
appropriate suffix for compiled object files for the platform.

.. function:: platform.bin(x)

Given a filename or list of filenames, replaces all suffixes with the
appropriate suffix for binary executable files for the platform.

.. function:: platform.dll(x)

Given a filename or list of filenames, replaces all suffixes with the
appropriate suffix for shared library files for the platform.

.. function:: platform.lib(x)

Given a filename or list of filenames, replaces all suffixes with the
appropriate suffix for static library files for the platform.

.. function:: platform.get_tool(name)

Given the name of a tool, returns an object that implements the respective
tools interface. The returned object may already consider environment
variables like ``CC`` and ``CXX``. Possible values for *name* are

.. csv-table::
  :header: "Name", "Description"
  :widths: 10, 90

  ``'c'``, C Compiler (see :ref:`compiler_interface`)
  ``'cpp'``, C++ Compiler (see :ref:`compiler_interface`)
  ``'ld'``, Linker (usually the same as C compiler on Linux/Mac OS) (see :ref:`linker_interface`)
  ``'ar'``, Static libary generator (archiver) (see :ref:`archiver_interface`)

.. _compiler_interface:

C/C++ Compiler Interface
------------------------

.. function:: compiler.compile(sources, frameworks=(), target_name=None, **kwargs)

+----------------------------------------------------------+
|:attr:`Target.meta<craftr.Target.meta>` output variables: |
+-----------------------+----------------------------------+
| None                  |                                  |
+-----------------------+----------------------------------+

**Known Implementations**

* :meth:`craftr.ext.compiler.msvc.MsvcCompiler.compile`
* :meth:`craftr.ext.compiler.llvm.LlvmCompiler.compile`

.. _linker_interface:

Linker Interface
----------------

.. function:: linker.link(output, inputs, output_type='bin', frameworks=(), target_name=None, **kwargs)

+----------------------------------------------------------+
|:attr:`Target.meta<craftr.Target.meta>` output variables: |
+-----------------------+----------------------------------+
|``'link_output'``      | Absolute output filename         |
+-----------------------+----------------------------------+

**Known Implementations**

* :meth:`craftr.ext.compiler.msvc.MsvcLinker.link`
* :meth:`craftr.ext.compiler.llvm.LlvmCompiler.link`

.. _archiver_interface:

Archiver Interface
------------------

.. function:: archiver.staticlib(output, inputs, target_name=None, **kwargs)

+----------------------------------------------------------+
|:attr:`Target.meta<craftr.Target.meta>` output variables: |
+-----------------------+----------------------------------+
|``'staticlib_output'`` | Absolute output filename         |
+-----------------------+----------------------------------+

**Known Implementations**

* :meth:`craftr.ext.compiler.msvc.MsvcAr.staticlib`
* :meth:`craftr.ext.unix.Ar.staticlib`

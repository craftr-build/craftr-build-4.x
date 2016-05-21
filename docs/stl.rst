The Craftr standard library
===========================

.. toctree::
  :maxdepth: 2

  stl/archive
  stl/compiler
  stl/git
  stl/platform
  stl/python
  stl/rules
  stl/unix

Platform Abstraction Interface
------------------------------

.. todo:: Documentation

.. _compiler_abstraction:

C/C++ Compiler Abstraction Interface
------------------------------------

This section only describes the interface for C/C++ compiler
implementations. Other compiler modules are described in their
respective module. There are implementations available for MSVC, LLVM and
GCC (which currently inherits the LLVM implementation).

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

.. todo:: Documentation

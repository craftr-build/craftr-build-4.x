Compiler Abstraction Interface
==============================

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


.. todo::

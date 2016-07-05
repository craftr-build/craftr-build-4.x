Using Craftr for Cython projects
================================

Craftr has convenient support for compiling Cython projects. The easy
way is to use :func:`~craftr.ext.cython.CythonCompiler.compile_project`.

.. code:: python

  from craftr import *
  from craftr.ext.compiler import cython

  cython.cythonc.compile_project(
    sources = path.glob('src/*.pyx'),
    python_bin = options.get('PYTHON', 'python'),
    additional_flags = ['-Xprofile=True'],
  )

For more control, the Cython invocation and C/C++ source file
compiling can be done manually. Below is the equivalent long
version of the above shorthand:

.. code:: python

  # craftr_module(cython_test)
  from craftr import *
  from craftr.ext import platform, python
  from craftr.ext.compiler import cython

  # 1. Find the compilation information for the target Python version.
  py = cython.PythonInfo(options.get('PYTHON', 'python'))

  # 2. Compile the .pyx files to C-files.
  pyxc_sources = cython.cythonc.compile(
    py_sources = path.glob('src/*.pyx'),
    python_version = py.major_version,
    cpp = False,
    additional_flags = ['-Xprofile=True']
  )

  # 3. Compile each C file to a shared library.
  for pyxfile, cfile in zip(pyxc_sources.inputs, pyxc_sources.outputs):
    platform.ld.link(
      output = path.setsuffix(pyxfile, py.conf['SO']),
      output_type = 'dll',
      keep_suffix = True, # don't let link() replace the suffix
      inputs = platform.cc.compile(
        sources = [cfile],
        frameworks = [py.fw],
        pic = True
      )
    )

Compiling with ``--embed``
--------------------------

Cython has an ``--embed`` command-line option that will cause the
generated C/C++ source code to contain a ``main()`` entry point.
You can just pass the ``main`` parameter to ``compile_project()``
and it will automatically generate an executable:

.. code:: python

  from craftr import *
  from craftr.ext import rules
  from craftr.ext.compiler import cython

  project = cython.cythonc.compile_project(
    main = path.local('main.pyx'),
    python_bin = options.get('PYTHON', 'python'),
  )

  # Allows you to invoke `craftr .run` to compile and run
  run = rules.run(project.main_bin)

.. note::

  You can combine compiling C-Extensions and an executable in a
  single call to :func:`~craftr.ext.compiler.cython.CythonCompiler.compile_project`.

Craftr Magic Explained
=======================

Craftr uses some magic tricks behind the scenes to make the interface
as convenient as possible. Most of the magic comes from the :mod:`craftr.magic`
module!

Proxies
-------

Craftr uses the :class:`werkzeug.local` module to provide the
:data:`craftr.session` and :data:`craftr.module` proxies that represent the
current session and currently executed module respectively. This is how the
:class:`craftr.Target` constructor (and subsequently all functions that create
a Target) knows in what module the target is being declared.

Target Name Deduction
---------------------

Target names are automatically deduced from the variable name that the
declared target is assigned to. This is enabled by parsing the bytecode
of the global stackframe of the current module. This is more convenient
that writing the name of the target twice by passing the ``name`` parameter
to the :class:`craftr.Target` constructor or a rule function.

.. code-block:: python

  objects = Target(
    command = 'gcc $in -o $out -c',
    inputs = sources,
    outputs = objects,
  )
  assert objects.name == 'objects'

Check the :func:`craftr.magic.get_assigned_name` function for details on the
implementation of this feature.

Craftr RTS
----------

The Craftr Runtime Server is a socket server that is started on a random
port on the localhost when Craftr is started. The ``craftr-rts`` command
can connect to that server and execute Python functions in the original
Craftr process. See :doc:`rts` for more information.

RTS & Python Tools
==================

Craftr allows you to create Python (command-line) Tools inside the ``Craftfile.py``
that Ninja can call through the **Craftr RTS** (runtime server). These tools are
all executed in the same Craftr process, thus being very efficient since the
``Craftfile.py`` does *not* need to be re-evaluated with each invocation.

You will see something like ``craftr-rts-invoke project.my_tool_target`` in the
``build.ninja`` file. When you run Craftr, it will create a socket server and
set the environment variable ``CRAFTR_RTS`` to the ``host:port`` combination.
``craftr-rts-invoke`` uses this address too communicate with the original
Craftr process and execute the desired function.

**Limitations**:

* You can not pipe into the ``craftr-rts-invoke`` script
* This feature can not be used if you do a build-only (eg. ``craftr -b``) since that
  will skip the execution step, unless you specify the ``--rts`` option which will
  keep the runtime server alive

**Example**:

This is from the ``craftr.ext.rules`` module:

.. code-block:: python

  class render_template(PythonTool):
    ''' This is a simple Python tool that can render a template file
    to a new file given a set of key/value pairs. Variables in the template
    are references by `${KEY}$`. There is currently not escape mechanism
    implemented. '''

    def __init__(self, template, output, **context):
      super().__init__([template], [output])
      self.template = template
      self.output = output
      self.context = context

    def __call__(self, args):
      with open(self.template) as src:
        content = src.read()
      for key, value in self.context.items():
        key = '${' + key + '}$'
        content = content.replace(key, value)
      with open(self.output, 'w') as dst:
        dst.write(content)

You can then use it like

.. code-block:: python

  my_target = render_template(
    template = path.local('the-template-file.txt'),
    output = 'the-rendered-template.txt',
    SOME_VARIABLE = 'Here was SOME_VARIABLE before!',
  )

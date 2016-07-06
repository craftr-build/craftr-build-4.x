Writing a Compiler Plugin
=========================

Craftr does not provide you with "one way to do it". There are multiple
ways you can make Craftr generate the command you need it to. You can
hard-code the command by creating a :class:`~craftr.Target` from scratch
or you can implement a *Generator Function*. What we do most of the time
is to implement a *Compiler Class* which inherits
:class:`craftr.ext.compiler._base.BaseCompiler`. It allows us to create
instances of "compiler interfaces" with different settings, which makes
these settings included in all procedures that generate targets.

Manual Targets
--------------

First things first though, here's a small example how you can just
manually create a target and have Craftr export that into the Ninja
manifest:

.. code:: python

  from craftr import path, Target

  main = Target(
    command = 'gcc $in -Wall -std=c++11 -o $out',
    inputs = path.glob('src/*.c'),
    outputs = ['main'],
  )

Notice how we specify just plain ``'main'`` as the output file: relative
filenames will be considered relative to the build directory! Craftr
automatically and *always* changes the working directory to the build
directory before executing any code.

Generator Functions
-------------------

Given the above simple GCC example, we can make things a bit more
customizable by implementing a function that generates the command
and target for us.

.. code:: python

  from craftr import path, Target

  def compile(sources, output, include=[], defines=[],
              lib=[], libpath=[], warn='1', std='c99'):
    command = ['gcc', '$in', '-W' + warn, '-std=' + std)
    command += ['-I' + x for x in include]
    command += ['-D' + x for x in defines]
    command += ['-L' + x for x in libpath]
    command += ['-l' + x for x in lib]
    return Target(command, sources, [output])

  main = compile(
    sources = path.glob('src/*.c'),
    output = 'main',
    warn = 'all',
    std = 'c++11'
  )

Using the TargetBuilder
-----------------------

While the above example already looks nice, it still has problems, or say,
complications: What will you do if you make use of some libraries and have
a number of additional include directories, defines, libpaths and libs? Just
concatenate them by hand?

Craftr's solution to this problem are :class:`~craftr.Framework`s. They
represent a collection of settings that can either be merged (e.g. for
things like include directories, defines, etc.) or the first available
setting can be used (e.g. for some one-off compiler option). In Craftr,
everything has frameworks. Just for example, a :class:`Target` has
a list of frameworks that have been used to generate it, thus if other
targets are created taking it as an input, they can automatically re-use
these frameworks and the user doesn't have to manually specify the framework
yet another time.

.. code:: python

  from craftr.ext.platform import cc, ld
  from craftr.ext.some_library import some_library_framework

  obj = cc.compile(
    sources = path.glob('src/*.c'),
    frameworks = [some_library_framework]
  )

  bin = ld.link(
    inputs = obj,
    output = 'main'
    # <: Note how we do not add "some_library_framework" in this call
  )

Now on to creating :class:`~craftr.Target` generato functions with the
:class:`~craftr.TargetBuilder`! This class handles a bunch of things,
but don't let yourself be confused about all these internals yet. They
are here for reference:

1. Evaluate a list of inputs that can consist of filenames or targets.
   Filenames are automatically normalized and for targets, the output
   files will be added to the input files and the frameworks will be
   included into the frameworks list.
2. Include a list of frameworks passed directly to the generator
   function.
3. Create a new :class:`Framework` from the additional keyword arguments
   passed to the generator function, but this framework will **not**
   be included in the generated targets framework list! You don't want
   your ``additional_flags`` passed to ``cc.compile()`` also being
   passed to ``ar.staticlib()`` automatically :)
4. All frameworks will then be expanded into a single list using
   :func:`~craftr.expand_inputs` (to flatten out framework dependencies).
5. A :class:`~craftr.FrameworkJoin` will be created from *all* frameworks
   (including the special ``**kwargs`` framework) to enable the generator
   function to read the settings.

Now, how Tracer would say it, "let's get to it already!". Note that I've
also added a ``language`` parameter which I did not in the previous examples.

.. code:: python

  from craftr import path, Target, TargetBuilder

  def compile(sources, output, frameworks=(), target_name=None, language='c', **kwargs):
    builder = TargetBuilder(sources, frameworks, kwargs, name=target_name)
    include = builder.merge('include')
    defines = builder.merge('defines')
    libpath = builder.merge('libpath')
    lib = builder.merge('lib')
    std = builder.get('std', 'c99')
    warn = builder.get('warn', '1')

    # Same code as above
    command = ['gcc', '-x', language, '$in', '-W' + warn, '-std=' + std)
    command += ['-I' + x for x in include]
    command += ['-D' + x for x in defines]
    command += ['-L' + x for x in libpath]
    command += ['-l' + x for x in lib]

    return builder.create_target(command, output)

  # Now we can use some other Craftfiles that expose Frameworks.
  # (You know, Craftr's not really popular yet so there's literally
  # only my own stuff right now :P)
  from craftr.ext.libs.nr_iterator import nr_iterator
  from craftr.ext.libs.nr_math3d import nr_math3d

  main = compile(
    language = 'c++',
    sources = path.glob('src/*.cpp'),
    output = 'main',
    frameworks = [nr_iterator, nr_math3d]
  )

Using the BaseCompiler
----------------------

It has a number of advantages, but you're free to use a plain generator
function as shown in the previous example! There's really not much to
be changed for using a :class:`~craftr.ext.compiler._base.BaseCompiler`
instead:

.. code:: python

  from craftr import path, Target
  from craftr.ext.compiler._base import BaseCompiler

  class SimpleGCC(BaseCompiler):

    def compile(self, sources, output, frameworks=(), target_name=None, language='c', **kwargs):
      builder = self.builder(sources, frameworks, kwargs, name=target_name)
      # ... exactly the same code as in the previous example

  gcc = SimpleGCC()
  main = gcc.compile(
    # ...
  )

However! you can now pass additional settings to the ``SimpleGCC()``
constructor that will be taken into account as well. Note that these are
considered last after everything else (``**kwargs``, frameworks list, input
target frameworks and only then the settings passed to the constructor).

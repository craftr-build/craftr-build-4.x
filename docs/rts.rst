Craftr Runtime Server (RTS)
===========================

Craftr allows you to embedd Python functions into the Ninja build chain
right from the Craftfile. Such Ninja targets will call the ``craftr-rts-invoke``
command which in turn communicates with the **Craftr Runtime Server** to run
a Python function. Craftr RTS targets are also called **tasks**.

Getting Started
---------------

Below you can find the simplest possible task that says hello to you!

.. code-block:: python

    # craftr_module(test)
    from craftr import task, info

    @task
    def hello(inputs, outputs):
      info("hello!")

Now that's not really interesting. But lets consider you want the task
to depend on another target. For example, you may want to write some
Python code to test a program against a dataset.

.. code-block:: python

    # craftr_module(test)
    from craftr import Target, path, shell, task, info, warn
    from craftr.ext.platform import cxx, ld

    # Compile our decipher program.
    decipher = ld.link(
      output = 'main',
      inputs = cxx.compile(sources = path.glob('src/*.cpp'), std = 'c++11')
    )

    # Create a task that tests the program by matching a test set of files.
    # But we need the decipher program to be compiled first.
    cipher_files = path.glob('data/*.dat')
    @task(inputs = cipher_files, implicit_deps = decipher)
    def test(inputs, outputs):
      prog = decipher.meta['link_output']
      path.makedirs('deciphered')
      # We don't have to use the inputs and outputs arguments, they'll
      # be just what you passed to the @task() decorator.
      for fn in cipher_files:
        # Output path for the deciphered file. Note that this will
        # automatically be outside of the working tree as Craftr changes cwd
        # to the build directory.
        out = 'deciphered/' + path.basename(fn) + '.txt'
        # Decipher the data.
        cmd = shell.format('cat {} | {} > {}', fn, prog, out)
        info('$', cmd)
        shell.run(cmd, shell=True)
        # Compare the output with the reference result.
        with open(out) as outfp:
          with open(fn + '.txt') as reffp:
            if outfp.read() != reffp.read():
              warn('test case {} failed'.format(path.basename(fn)))
            else:
              info('test case {} succeeded.'.format(path.basename(fn)))

And you can run the ``test`` task with Craftr like so:

::

    niklas ~/Desktop/test $ craftr -eb .test
    craftr: [INFO ]: Changed directory to "build"
    [3/3] craftr-rts-invoke test.test
    craftr: [INFO ]: $ cat /Users/niklas/Desktop/test/data/cipher01.dat | test/main > deciphered/cipher01.dat.txt
    craftr: [INFO ]: test case cipher01.dat succeeded.
    craftr: [INFO ]: $ cat /Users/niklas/Desktop/test/data/cipher02.dat | test/main > deciphered/cipher02.dat.txt
    craftr: [INFO ]: test case cipher02.dat succeeded.

Limitations
-----------

* You can not pipe into the ``craftr-rts-invoke`` script
* This feature requires Craftr to actually execute all modules and
  be alive to run the Craftr RTS module, thus you can not use RTS
  by running Ninja manually
* Due to the above limitation, using the ``-b`` flag to only build
  with targets that require RTS will Craftr **not allow to skip**
  the execution phase

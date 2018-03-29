## examples/pyfreeze

Example for building a frozen Python application.

    $ craftr -t python.freeze -- -o frozen_src hello.py
    $ craftr -cb main:cxx.run

### To do

* [ ] Automatically copy required shared libraries to the build output folder

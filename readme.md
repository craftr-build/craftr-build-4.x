# Craftr [![Build Status](https://travis-ci.org/craftr-build/craftr.svg?branch=master)](https://travis-ci.org/craftr-build/craftr) [![Gitter](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/craftr-build/craftr?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

Craftr is a pythonic meta build system for Ninja that is fast,
cross-platform, easy to use and allows for fine grain control of
the build process. In Craftr, build definitions are generated
using Python scripts.

__The simplest possible example__

```python
# craftr_module(simple)

sources = ['src/main.c', 'src/utils.c']
include_dirs = ['include']

target(
  'Objects',
  inputs = sources,
  outputs = move(sources, 'src', 'build/obj', suffix='o'),
  foreach = True,
  command = ['ccache', 'gcc', '-Wall', '-c', '%%in', '-o', '%%out'],
  description = 'Building Object %%out')

target(
  'Executable',
  inputs = Objects.outputs,
  outputs = executable,
  command = ['ccache', 'gcc', '%%in', '-o', '%%out'],
  description = 'Buikding Executable %%out')
```

To build, run

    craftr export
    ninja


__Installation__

Grab the stable release from this repository and install using Pip.
You might want to do so in a virtualenv. To always use the latest
version of Craftr, consider using an editable Pip installation (`-e`)
and update by pulling the latest changes into the repository.

    git clone git@github.com:craftr-build/craftr.git && cd craftr
    virtualenv .env && source .env/bin/activate
    pip install -e .

__Todo__

- [ ] Built-in Craftr modules with a common interface to modern
      compilers like GCC, Clang and MSVC
- [ ] Find ways to simplify build definitions for projects with
      standard structures
- [ ] Support for auto dependencies

__Requirements__

- Python 3.3 or greater
- [glob2](pypi.python.org/pypi/glob2)
- [colorama](pypi.python.org/pypi/colorama) (optional)

----------

Copyright (C) 2015 Niklas Rosenstein

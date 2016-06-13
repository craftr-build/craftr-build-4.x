# Craftr

[![PyPI Version](https://img.shields.io/pypi/v/craftr-build.svg)](https://pypi.python.org/pypi/craftr-build)
[![Travis CI](https://travis-ci.org/craftr-build/craftr.svg)](https://travis-ci.org/craftr-build/craftr)
[![Documentation Status](https://readthedocs.org/projects/craftr/badge/?version=latest)](http://craftr.readthedocs.io/en/latest/?badge=latest)

Craftr is a next generation build system based on [Ninja][] and [Python][].
And don't worry, it isn't like waf or SCons!

* [Changelog (latest)][Changelog]
* [Documentation (latest)](https://craftr.readthedocs.io/en/latest/)
* [Documentation (stable)](https://craftr.readthedocs.io/en/stable/)
* [List of third-party extension modules](https://github.com/craftr-build/craftr/wiki/Craftr-Extensions)
* [Projects using Craftr](https://github.com/craftr-build/craftr/wiki/Projects-using-Craftr)

### Contribute

I welcome all contributions, feedback and suggestions! If you have any of
those or just want to chat, ping me on [twitter][], by [mail][] or open a [new issue][]!

### Requirements

- [Ninja][]
- [Python][] 3.4 or higher
- see [requirements.txt](requirements.txt)
* [Pandoc][] when installing from the Git repository

### Installation

    pip install craftr-build

To install from the Git repository, use the `-e` flag to be able to update
Craftr by simply pulling the latest changes from the remote repository.

    git clone https://github.com/craftr-build/craftr.git && cd craftr
    pip install -e .

----

MIT Licensed &ndash; Copyright &copy; 2016  Niklas Rosenstein

  [new issue]: https://github.com/craftr-build/craftr/issues/new
  [twitter]: https://twitter.com/rosensteinn
  [mail]: mailto:rosensteinniklas@gmail.com
  [Ninja]: https://github.com/ninja-build/ninja
  [Python]: https://www.python.org
  [Pandoc]: http://pandoc.org
  [Changelog]: docs/changelog.rst

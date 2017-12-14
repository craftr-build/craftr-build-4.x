<img align="right" src=".assets/craftr-logo.png">

## The Craftr Build System

<a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
<a href="https://travis-ci.org/craftr-build/craftr"><img src="https://travis-ci.org/craftr-build/craftr.svg?branch=craftr-3.x"></a>
<a href="https://ci.appveyor.com/project/NiklasRosenstein/craftr"><img src="https://ci.appveyor.com/api/projects/status/6v01441cdq0s7mik?svg=true"></a>
*Version 3.0.0-dev*

&mdash; A modular language-independent build system.

### Features

  [Node.py Package Manager]: https://github.com/nodepy/nodepy-pm

* Craftr is installed on a **per-project** basis
* Build scripts are written in Python (with some sugar)
* Supports building C#, Java and C++ projects out of the box

### Installation

Make sure you have at least [Python 3.6](https://www.python.org/downloads/release/python-363/)
installed on your system, then follow these steps:

    # Install Node.py (https://nodepy.org)
    pip3.6 install --user git+https://github.com/nodepy/nodepy.git@develop

    # Install the Node.py Package Manager
    nodepy https://nodepy.org/install-pm -g master

    # Install Craftr into your current project directory
    cd ~/repos/myproject
    nodepy-pm install git+https://github.com/craftr-build/craftr.git@craftr-3.x
    export PATH=.nodepy/bin:${PATH}

### Quickstart

    craftr --quickstart {java,csharp,c,cpp}

This will create a `BUILD.cr.py` file from a template and a `nodepy.json`
manifest to keep track of your dependencies (just Craftr, for the start).

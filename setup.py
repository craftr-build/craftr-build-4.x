# Copyright (C) 2016  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from functools import partial
from setuptools import setup, find_packages

import os
import pip.req, pip.download
import shutil
import sys

if sys.version < '3.4':
  sys.exit("Craftr requires Python 3.4 or greater")

# Convert README.md to reST.
if os.path.isfile('README.md'):
  if os.system('pandoc -s README.md -o README.rst') != 0:
    print('-----------------------------------------------------------------')
    print('WARNING: README.rst could not be generated, pandoc command failed')
    print('-----------------------------------------------------------------')
    if sys.stdout.isatty():
      input("Enter to continue... ")

# parse_requirements() interface has changed in Pip 6.0
from pip.req import parse_requirements
if pip.__version__ >= '6.0':
  parse_requirements = partial(parse_requirements, session=pip.download.PipSession())

if os.path.isfile('README.rst'):
  with open('README.rst', encoding='utf8') as fp:
    long_description = fp.read()
else:
  long_description = None

# Parse the requirements from requirements.txt
requirements = [str(x.req) for x in parse_requirements('requirements.txt')]

setup(
  name = 'craftr-build',
  version = '1.1.0.2',
  description = 'next generation build system based on Ninja and Python',
  long_description = long_description,
  classifiers = [
    "Topic :: Software Development",
    "Topic :: Software Development :: Build Tools",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: Implementation :: CPython",
    "Operating System :: Unix",
    "Operating System :: POSIX :: Linux",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: MacOS",
    "Operating System :: MacOS :: MacOS X",
    "License :: OSI Approved :: MIT License"
  ],
  platforms = ['Windows', 'Mac OS', 'Linux'],

  license = 'MIT',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas(at)gmail.com',
  url = 'https://github.com/craftr-build/craftr',

  entry_points = dict(
    console_scripts = [
      "craftr = craftr.__main__:main",
      "craftr-rts-invoke = craftr.rts:client_main",
    ]
  ),

  # Although craftr.lib is not a real package, we need to include it
  # as otherwise Python Eggs of Craftr will not contain the files of
  # the craftr/lib directory.
  packages = ['craftr', 'craftr.lib'],
  package_dir = {'': '.'},
  package_data = {
    'craftr': ['lib/*.craftr']
  },
  install_requires = requirements,
)

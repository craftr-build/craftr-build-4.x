# The Craftr build system
# Copyright (C) 2016  Niklas Rosenstein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pip.req import parse_requirements
from setuptools import setup, find_packages

import functools
import os
import pip
import sys

if sys.version < '3.4' or sys.version >= '3.6':
  print('-----------------------------------------------------------------')
  print("WARNING: Craftr officially supports Python 3.4, 3.5")
  print("WARNING: Your current version is Python {}".format(sys.version[:5]))
  print('-----------------------------------------------------------------')

# parse_requirements() interface has changed in Pip 6.0
if pip.__version__ >= '6.0':
  parse_requirements = functools.partial(
      parse_requirements, session=pip.download.PipSession())

# Convert README.md to reST.
if os.path.isfile('README.md'):
  if os.system('pandoc -s README.md -o README.rst') != 0:
    print('-----------------------------------------------------------------')
    print('WARNING: README.rst could not be generated, pandoc command failed')
    print('-----------------------------------------------------------------')
    if sys.stdout.isatty():
      input("Enter to continue... ")

if os.path.isfile('README.rst'):
  with open('README.rst', encoding='utf8') as fp:
    long_description = fp.read()
else:
  long_description = None

setup(
  name = 'craftr-build',
  version = '2.0.0.dev1',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  url = 'https://gitlab.niklasrosenstein.com/niklas/craftr',
  install_requires = [str(x.req) for x in parse_requirements('requirements.txt')],
  entry_points = dict(
    console_scripts = [
      'craftr = craftr.__main__:main_and_exit'
    ]
  ),
  packages = find_packages(),
  package_data = {
    'craftr': ['stl/**/*', 'stl_auxiliary/**/*']
  },
  license = 'MIT',
  classifiers = [
    "Topic :: Software Development",
    "Topic :: Software Development :: Build Tools",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: Implementation :: CPython",
    "License :: OSI Approved :: MIT License"
  ],
)

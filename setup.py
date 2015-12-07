# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import os
import sys
from setuptools import setup, find_packages

if sys.version < '3.4':
  sys.exit("Craftr requires Python 3.4 or greater.")

script = 'bin/craftr.py' if os.name == 'nt' else 'bin/craftr'

setup(
  name='craftr-build',
  version='0.20.0',
  author='Niklas Rosenstein',
  author_email='rosensteinniklas(at)gmail.com',
  url='https://github.com/craftr-build/craftr',
  install_requires=['glob2', 'werkzeug'],
  scripts=[script],
  packages=find_packages('.'),
  package_dir={'': '.'},
  package_data={
    'craftr': ['lib/*.craftr']
  },
)

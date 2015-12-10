# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

from pip.req import parse_requirements
from setuptools import setup, find_packages
import os
import sys

if sys.version < '3.4':
  sys.exit("Craftr requires Python 3.4 or greater.")

requires = [str(x.req) for x in parse_requirements('requirements.txt')]
script = 'bin/craftr.py' if os.name == 'nt' else 'bin/craftr'

setup(
  name='craftr-build',
  version='0.20.0',
  author='Niklas Rosenstein',
  author_email='rosensteinniklas(at)gmail.com',
  url='https://github.com/craftr-build/craftr',
  install_requires=requires,
  scripts=[script],
  packages=find_packages('.'),
  package_dir={'': '.'},
  package_data={
    'craftr': ['lib/*.craftr']
  },
)

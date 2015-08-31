# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

from setuptools import setup
import os

script = 'scripts/craftr.py' if os.name == 'nt' else 'scripts/craftr'

setup(
  name='craftr-build',
  version='0.0.9',
  author='Niklas Rosenstein',
  author_email='rosensteinniklas(at)gmail.com',
  install_requires=['glob2', 'colorama'],
  scripts=[script],
)

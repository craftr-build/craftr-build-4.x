# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

from functools import partial
from setuptools import setup, find_packages

import os
import pip.req, pip.download
import shutil
import sys

if sys.version < '3.4':
  sys.exit("Craftr requires Python 3.4 or greater.")

# parse_requirements() interface has changed in Pip 6.0
from pip.req import parse_requirements
if pip.__version__ >= '6.0':
  parse_requirements = partial(parse_requirements, session=pip.download.PipSession())

scripts = ['bin/craftr', 'bin/craftr-rts']

# On Windows, we need this scripts with a .py suffix.
if os.name == 'nt':
  if not os.path.isdir('build/bin'):
    os.makedirs('build/bin')
  new_scripts = [os.path.join('build', x) + '.py' for x in scripts]
  for src, dst in zip(scripts, new_scripts):
    shutil.copy2(src, dst)
  scripts = new_scripts

# Parse the requirements from requirements.txt
requirements = [str(x.req) for x in parse_requirements('requirements.txt')]

setup(
  name='craftr-build',
  version='0.20.0',
  author='Niklas Rosenstein',
  author_email='rosensteinniklas(at)gmail.com',
  url='https://github.com/craftr-build/craftr',
  install_requires=requirements,
  scripts=scripts,
  packages=find_packages('.'),
  package_dir={'': '.'},
  package_data={
    'craftr': ['lib/*.craftr']
  },
)

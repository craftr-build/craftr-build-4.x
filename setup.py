# Copyright (C) 2015  Niklas Rosenstein
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

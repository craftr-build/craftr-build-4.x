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
import pip

# parse_requirements() interface has changed in Pip 6.0
if pip.__version__ >= '6.0':
  parse_requirements = functools.partial(
      parse_requirements, session=pip.download.PipSession())

setup(
  name = 'craftr-build',
  version = '2.0.0-dev',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  url = 'https://gitlab.niklasrosenstein.com/niklas/craftr',
  packages = find_packages(),
  install_requires = [str(x.req) for x in parse_requirements('requirements.txt')],
  entry_points = dict(
    console_scripts = [
      'craftr = craftr.__main__:main_and_exit'
    ]
  )
)

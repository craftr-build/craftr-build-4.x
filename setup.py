
from setuptools import setup, find_packages
from pip.req import parse_requirements

import functools
import pip

# parse_requirements() interface has changed in Pip 6.0
if pip.__version__ >= '6.0':
  parse_requirements = functools.partial(
    parse_requirements, session=pip.download.PipSession())

setup(
  name = 'craftr-build',
  version = '3.0.1-dev',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'A meta build system in Python with a custom DSL.',
  license = 'MIT',
  url = 'https://github.com/craftr-build/craftr',
  install_requires = [str(x.req) for x in parse_requirements('requirements.txt')],
  packages = find_packages(),
  entry_points = dict(
    console_scripts =   [
      'craftr = craftr.__main__:_entry_point'
    ]
  )
)

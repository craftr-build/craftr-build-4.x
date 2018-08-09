
import io
import setuptools

with io.open('requirements.txt') as fp:
  requirements = [x.strip() for x in fp.readlines()]

setuptools.setup(
  name = 'craftr-build',
  version = '4.0.0.dev0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  license = 'MIT',
  url = 'https://github.com/craftr-build/craftr',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  entry_points = {
    'console_scripts': ['craftr=craftr.main:main']
  },
  install_requires = requirements
)

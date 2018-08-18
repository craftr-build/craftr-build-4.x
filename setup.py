
import io
import setuptools

with io.open('requirements.txt') as fp:
  requirements = [x.strip() for x in fp.readlines()]

with io.open('README.md', encoding='utf8') as fp:
  readme = fp.read()

setuptools.setup(
  name = 'craftr-build',
  version = '4.0.0.dev2',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'A Python based meta build system for various languages.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  license = 'MIT',
  url = 'https://github.com/craftr-build/craftr',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  include_package_data = True,
  install_requires = requirements,
  entry_points = {
    'console_scripts': ['craftr=craftr.main:main']
  }
)

"""
Command-line entry point for the Craftr build system.
"""

import argparse
import functools
import os
import shutil
import sys

import {reindent, ReindentHelpFormatter} from 'craftr/utils/text'

error = functools.partial(print, file=sys.stderr)


parser = argparse.ArgumentParser(
  formatter_class=ReindentHelpFormatter,
  prog='craftr',
  description='''
    The Craftr Build System
    -----------------------

    Craftr is a modular language-indepenent build system that is written in
    Python. It's core features are cross-platform compatibility, extensibility
    as well as performance and a Python as a powerful tool for customizing
    build steps.
  ''',
)

parser.add_argument(
  '--quickstart',
  metavar='LANGUAGE',
  nargs='?',
  default=NotImplemented,
  help='Generate Craftr project files from a template for the specified '
       'LANGUAGE. A BUILD.cr.py and nodepy.json file will be created.',
)

parser.add_argument(
  '--backend',
  help='The backend to use for building. The last (explicitly) used backend '
       'is remembered when using the --prepare-build or --build options. If '
       'this option is not defined, it is read from the `build.backend` '
       'configuration value. Defaults to `ninja`.'
)

parser.add_argument(
  '--release',
  action='store_true',
  help='Configure a release build. This option will set the `craftr.release` '
       'configuration value and also the `release` member of the Craftr '
       'core module.'
)

parser.add_argument(
  '--configure',
  nargs='?',
  default='BUILD.cr.py',
  help='Execute the build script and generate a JSON database file that '
       'contains all the build information.'
)

parser.add_argument(
  '--prepare-build',
  action='store_true',
  help='Prepare the build process by generating all the data for the '
       'selected build backend, but not actually execute the build. Use '
       'this option if you want to invoke the build backend manually instead '
       'of via the --build option.'
)

parser.add_argument(
  '--build',
  action='store_true',
  help='Load the build configuration from the --configure step and execute '
       'the build process using the configured backend. Implies the '
       '--prepare-build option.'
)


def main(argv=None):
  args = parser.parse_args(argv)
  if args.quickstart is not NotImplemented:
    return quickstart(language=args.quickstart)


def quickstart(language):
  templates_dir = module.package.directory.joinpath('templates')
  if not templates_dir.is_dir():
    error('fatal: template directory does not exist')
    return 1

  if language is None:
    language = 'generic'
  template_file = templates_dir.joinpath('BUILD.cr.py.{}.template'.format(language))
  if not template_file.is_file():
    error('fatal: no template for "{}"'.format(language))
    return 1

  manifest_template = templates_dir.joinpath('nodepy.json.template')
  if os.path.isfile('nodepy.json'):
    print('note: nodepy.json already exists in current directory.')
    print('      The file will not be overwritten from the template.')
  else:
    with manifest_template.open() as src:
      data = src.read()
    data.replace('{NAME}', project_name)
    data.replace('{VERSION}', project_version)
    with open('nodepy.json', 'w') as dst:
      dst.write(data)
    print('created: nodepy.json')

  if os.path.isfile('BUILD.cr.py'):
    print('note: BUILD.cr.py already exists in the current directory.')
    print('      The file will not be overwritten from the template.')
  else:
    shutil.copy2(str(template_file), 'BUILD.cr.py')
    print('created: BUILD.cr.py')


if require.main == module:
  sys.exit(main())

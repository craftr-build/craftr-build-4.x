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

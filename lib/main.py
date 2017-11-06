"""
Command-line entry point for Craftr.
"""

import argparse
import os
import sys
import path from './utils/path'
import {ActionProgress} from './core/actions'
import {Session} from './core/session'

parser = argparse.ArgumentParser()
parser.add_argument('projectdir', nargs='?', default='.')
parser.add_argument('-b', '--builddir')
parser.add_argument('-c', '--config')

def main():
  args = parser.parse_args()

  # The builddir can not be the same as the projectdir.
  args.projectdir = path.canonical(args.projectdir)
  if args.projectdir == os.getcwd() and not args.builddir:
    print('fatal: projectdir can not be current directory unless\n'
          '       an alternative builddir is specified.')
    return 1

  if not args.builddir:
    args.builddir = '.'

  # Default configuration is the `craftrconfig.toml` in the build
  # directory, or if that doesn't exist, from the cwd.
  if not args.config:
    config_filename = os.path.join(args.builddir, 'craftrconfig.toml')
    if not os.path.isfile(config_filename):
      config_filename = './craftrconfig.toml'
      if not os.path.isfile(config_filename):
        config_filename = None
    args.config = config_filename

  # Initialize our build session.
  session = Session(args.projectdir, args.builddir)
  if args.config:
    session.config.read(args.config)

  # Find and execute the build script.
  filename = os.path.join(args.projectdir, './Craftrfile.py')
  module = require.new(session.projectdir).resolve(filename)
  with session, require.context.push_main(module):
    require.context.load_module(module)

    tg = session.build_target_graph()
    ag = tg.translate()
    code = 0
    for action in ag.topo_sort():
      if action.check_skip(): continue
      print('[{}]: {}'.format(action.long_name, action.data.get_display(action)))
      progress = ActionProgress(do_buffering=False)
      code = action.execute_with(progress)
      if code != 0:
        print('fatal: action {!r} exited with {}'.format(action.long_name, code))
        return code


if require.main == module:
  sys.exit(main())

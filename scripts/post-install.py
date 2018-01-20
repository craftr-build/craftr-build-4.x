# This script is called after the Craftr core package is installed and will
# install the Craftr standard library.

assert 'installer' in globals(), "this script must be run in the post-install step."

import json
import {stream} from 'craftr/utils'

# Collect all standard library packages and create a dependency graph.
packages = {}
for directory in module.directory.joinpath('../lib/@craftr').iterdir():
  with open(str(directory.joinpath('nodepy.json'))) as fp:
    pkgdata = {
      'directory': str(directory),
      'manifest': json.load(fp)
    }
  packages['@craftr/' + directory.name] = pkgdata

def install_order(pkg, visited=None):
  if visited is None: visited = []
  if pkg in visited: raise RuntimeError('cyclic dependency: ' + ' -> '.join(visited + [pkg]))
  visited.append(pkg)
  for dep in packages[pkg]['manifest']['dependencies'].keys():
    if dep in packages:
      yield from install_order(dep, visited)
  yield pkg
  assert visited.pop() == pkg

# Install the packages in subsequent installation steps, but hide the output
# unless there's an error.
import io, sys
buffer = io.StringIO()
oldio = (sys.stdout, sys.stderr)
sys.stdout = sys.stderr = buffer
try:
  success = True
  for name in stream.unique(stream.concat(install_order(k) for k in packages)):
    pkgdata = packages[name]
    success, manifest = installer.install_from_directory(
      pkgdata['directory'],
      develop=True,
      expect=(name, None),
      pure=True
    )
    if not success:
      break
finally:
  sys.stdout, sys.stderr = oldio

if success:
  print('  Installed Craftr standard library.')
else:
  print('  Error installing Craftr standard library.')
  print(buffer.getvalue())

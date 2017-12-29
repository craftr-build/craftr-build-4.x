"""
Finds MinGW installations on Windows.
"""

import os
import subprocess
import sys
import utils from 'craftr/utils'
import sh from 'craftr/utils/sh'
import winreg from 'craftr/utils/winreg'


class MingwInstallation(utils.named):

  __annotations__ = [
    ('location', str),
    ('is_64', bool)
  ]

  @property
  def batfile(self):
    if self.is_64:
      return os.path.join(self.location, 'mingw-w64.bat')
    else:
      return os.path.join(self.location, 'mingw.bat')

  @property
  def binpath(self):
    if self.is_64:
      return os.path.join(self.location, 'mingw64', 'bin')
    else:
      return os.path.join(self.location, 'mingw', 'bin')

  def environ(self):
    env = os.environ.copy()
    env['PATH'] = self.binpath + os.pathsep + env['PATH']
    return env

  @classmethod
  def list(cls):
    """
    Searches for MinGW installations on the system using the Windows Registry.
    """

    keys = []
    keys.append(winreg.HKEY_LOCAL_MACHINE.key('SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall'))
    keys.append(winreg.HKEY_LOCAL_MACHINE.key('SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall'))

    results = []
    for key in utils.stream.concat(x.keys() for x in keys):
      if 'posix' in key.name or 'win32' in key.name:
        publisher = key.value('Publisher').data
        if 'mingw' in publisher.lower():
          try:
            location = key.value('InstallLocation').data
          except FileNotFoundError:
            location = os.path.dirname(key.value('UninstallString').data)
          results.append(cls(location, '64' in publisher))
    return results


def main(argv=None):
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('argv', nargs='...')
  args = parser.parse_args(argv)

  if not args.argv:
    for i, inst in enumerate(MingwInstallation.list()):
      print('- Location:'.format(i), inst.location)
      print('  Use Options:', '--options cxx.compiler=mingw:{}'.format(i))
      print('  Architecture:', 'x64' if inst.is_64 else 'x86')
      print()
  else:
    inst = MingwInstallation.list()[0]
    with sh.override_environ(inst.environ()):
      return subprocess.call(args.argv)


if require.main == module:
  sys.exit(main())

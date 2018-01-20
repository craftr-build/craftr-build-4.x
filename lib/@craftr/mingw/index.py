"""
Finds MinGW installations on Windows.
"""

import os
import re
import subprocess
import sys
import {sh, utils} from 'craftr'
import winreg from 'craftr/utils/winreg'


class MingwInstallation(utils.named):

  __annotations__ = [
    ('binpath', str),
    ('_is_64', bool, None),
    ('_gccinfo', dict, None),
    ('_environ', dict, None),
  ]

  @property
  def is_64(self):
    if self._is_64 is not None:
      return self._is_64
    return '64' in self.gccinfo['target']

  @property
  def gccinfo(self):
    if self._gccinfo is None:
      with sh.override_environ(self.environ):
        output = sh.check_output(['gcc', '-v'], stderr=sh.STDOUT).decode()
        target = re.search('Target:\s+(.*)$', output, re.M | re.I).group(1).strip()
        version = re.search('\w+\s+version\s+([\d\.]+)', output, re.M | re.I).group(1)
      self._gccinfo = {'target': target, 'version': version}
    return self._gccinfo

  @property
  def environ(self):
    if self._environ is None:
      self._environ = os.environ.copy()
      self._environ['PATH'] = self.binpath + os.pathsep + self._environ['PATH']
    return self._environ

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
          is_64 = '64' in publisher
          if is_64:
            location = os.path.join(location, 'mingw64', 'bin')
          else:
            location = os.path.join(location, 'mingw', 'bin')
          results.append(cls(location, is_64))
    return results


def main(argv=None):
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('argv', nargs='...')
  args = parser.parse_args(argv)

  if not args.argv:
    for i, inst in enumerate(MingwInstallation.list()):
      print('- Location:'.format(i), inst.binpath)
      print('  Use Options:', '--options cxx.compiler=mingw:{}'.format(i))
      print('  Architecture:', 'x64' if inst.is_64 else 'x86')
      print('  Target:', inst.gccinfo['target'])
      print('  Gcc Version:', inst.gccinfo['version'])
      print()
  else:
    inst = MingwInstallation.list()[0]
    with sh.override_environ(inst.environ):
      return subprocess.call(args.argv)


if require.main == module:
  sys.exit(main())

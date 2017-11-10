"""
Detect MSVC installations on the current system (Windows only).
"""

__all__ = ['MsvcInstallation', 'MsvcToolkit']

import contextlib
import functools
import json
import operator
import os
import platform
import re
import subprocess
import sys
import tempfile
import typing as t
import path from '../utils/path'
import sh from '../utils/sh'
import {NamedObject} from '../utils/types'
import craftr from '../public'

def get_arch():
  arch = platform.machine().lower()
  if arch == 'amd64':
    arch = 'x86_64'
  return arch


class MsvcInstallation(NamedObject):
  """
  Represents an MSVC installation directory.
  """

  version: int
  directory: str

  @property
  @functools.lru_cache()
  def vcvarsall(self):
    """
    Generates the path to the `vcvarsall.bat`.
    """

    if self.version >= 2017:
      return os.path.join(self.directory, 'VC', 'Auxiliary', 'Build', 'vcvarsall.bat')
    else:
      return os.path.join(self.directory, 'VC', 'vcvarsall.bat')

  @functools.lru_cache()
  def environ(self, arch=None, platform_type=None, sdk_version=None):
    """
    Executes the `vcvarsall.bat` of this installation with the specified
    *arch* and returns the environment dictionary after that script
    initialized it. If *arch* is omitted, it defaults to the current
    platform's architecture.

    If the specified architecture is incorrect or anything else happens that
    results in the `vcvarsall.bat` to not update the environment, a
    #ValueError is raised.

    If the `vcvarsall.bat` can not be exeuted, #subprocess.CalledProcessError
    is raised.
    """

    arch = get_arch()
    if arch == 'x86_64':
      arch = 'x86_amd64'

    cmd = [self.vcvarsall, arch]
    if platform_type:
      cmd.append(platform_type)
    if sdk_version:
      cmd.append(sdk_version)

    key = 'JSONOUTPUTBEGIN:'
    pyprint = 'import os, json; print("{}" + json.dumps(dict(os.environ)))'\
      .format(key)

    cmd = sh.join(cmd + [sh.safe('&&'), sys.executable, '-c', pyprint])
    output = subprocess.check_output(cmd, shell=True).decode()

    key = 'JSONOUTPUTBEGIN:'
    env = json.loads(output[output.find(key) + len(key):])
    if env == os.environ:
      content = output[:output.find(key)]
      raise ValueError('failed: ' + cmd + '\n\n' + content)

    return env

  @classmethod
  @functools.lru_cache()
  def list(cls):
    """
    List all available MSVC installations.
    """

    # Check all VS_COMNTOOLS environment variables.
    results = []
    for key, value in os.environ.items():
      if not (key.startswith('VS') and key.endswith('COMNTOOLS')):
        continue
      try:
        ver = int(key[2:-9])
      except ValueError:
        continue

      # Clean up the directory name.
      value = value.rstrip('\\')
      if not value or not os.path.isdir(value):
        continue
      if os.path.basename(value).lower() == 'tools':
        # The VS_COMNTOOLS variable points to the Common7\Tools
        # subdirectory, usually.
        value = os.path.dirname(os.path.dirname(value))

      results.append(cls(version=ver, directory=value))

    have_versions = set(x.version for x in results)

    # Special handling for MSVC 2017.
    # TODO: Can MSVC 2017 be installed in an alternative location?
    if 2017 not in have_versions:
      programfiles = os.getenv('ProgramFiles(x86)', '') or os.getenv('ProgramFiles', '')
      if programfiles:
        vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Community')
        if not os.path.isdir(vspath):
          vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Professional')
        if not os.path.isdir(vspath):
          vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Enterprise')
        if os.path.isdir(vspath):
          results.append(cls(2017, vspath))

    # TODO: Special handling for newer MSVC versions?

    return sorted(results, key=operator.attrgetter('version'), reverse=True)


class AsDictJSONEncoder(json.JSONEncoder):

  def default(self, obj):
    if hasattr(obj, '_asdict'):
      return obj._asdict()
    elif hasattr(obj, 'asdict'):
      return obj.asdict()
    return super().default(obj)


class ClInfo(NamedObject):

  version: str
  version_str: str
  target: str
  msvc_deps_prefix: str = None
  assembler_program: str
  link_program: str
  lib_program: str

  VERSION_REGEX = re.compile(r'compiler\s+version\s*([\d\.]+)\s*\w+\s*(x\w+)', re.I | re.M)

  @classmethod
  def from_program(cls, program, env=None):
    with sh.override_environ(env or {}):
      version_output = subprocess.check_output(['cl'], stderr=subprocess.STDOUT).decode()
    match = cls.VERSION_REGEX.search(version_output)
    if not match:
      raise RuntimeError('ClInfo could not be detected from {!r}'
        .format(program))

    version = match.group(1)
    arch = match.group(2)

    # Determine the msvc_deps_prefix by making a small test. The
    # compilation will not succeed since no entry point is defined.
    deps_prefix = None
    with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as fp:
      fp.write(b'#include <stddef.h>\n')
      fp.close()
      command = [program, '/Zs', '/showIncludes', fp.name]
      try:
        with sh.override_environ(env or {}):
          output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode()
      finally:
        os.remove(fp.name)

      # Find the "Note: including file:" in the current language. We
      # assume that the structure is the same, only the words different.
      # After the logo output follows the filename followed by the include
      # notices.
      for line in output.split('\n'):
        if 'stddef.h' in line:
          if 'C1083' in line or 'C1034' in line:
            # C1083: can not open include file
            # C1034: no include path sep
            msg = 'MSVC can not compile a simple C program.\n  Program: {}\n  Output:\n\n{}'
            raise ToolDetectionError(msg.format(program, output))
          match = re.search('[\w\s]+:[\w\s]+:', line)
          if match:
            deps_prefix = match.group(0)

    return cls(
      version = version,
      version_str = version_output.split('\n', 1)[0].strip(),
      target = arch,
      msvc_deps_prefix = deps_prefix,
      assembler_program = 'ml64' if arch == 'x64' else 'ml',
      link_program = 'link',
      lib_program = 'lib'
    )


class MsvcToolkit(NamedObject):
  """
  Similar to a #MsvcInstallation, this class represents an MSVC
  installation, however it is fixed to a specific target architecture and
  Windows SDK, etc. Additionally, it can be saved to and loaded from disk.
  """

  @staticmethod
  def CACHEFILE():
    return path.join(craftr.session.builddir, '.config', 'msvc-toolkit.json')

  CSC_VERSION_REGEX = re.compile(r'compiler\s+version\s+([\d\.]+)', re.I | re.M)

  version: int
  directory: str
  environ: dict
  arch: str
  platform_type: str = None
  sdk_version: str = None
  _csc_version: str = None
  _vbc_version: str = None
  _cl_info: ClInfo = None

  @classmethod
  def from_installation(cls, inst, arch=None, platform_type=None, sdk_version=None):
    environ = inst.environ(arch, platform_type, sdk_version)
    return cls(inst.version, inst.directory, environ, arch, platform_type, sdk_version)

  @classmethod
  def from_file(cls, file):
    if isinstance(file, str):
      with open(file, 'r') as fp:
        return cls.from_file(fp)
    data = json.load(file)
    if data.get('_cl_info'):
      data['_cl_info'] = ClInfo(**data['_cl_info'])
    return cls(**data)

  @classmethod
  @functools.lru_cache()
  def from_config(cls):
    installations = MsvcInstallation.list()
    if not installations:
      raise RuntimeError('Unable to detect any MSVC installation. Is it installed?')

    version = craftr.session.config.get('msvc.version')
    if version:
      version = int(version)
      install = next((x for x in installations if x.version == version), None)
      if not install:
        raise RuntimeError('MSVC version "{}" is not available.'.format(version))
    else:
      install = installations[0]
      version = install.version

    arch = craftr.session.config.get('msvc.arch', get_arch())
    platform_type = craftr.session.config.get('msvc.platform_type')
    sdk_version = craftr.session.config.get('msvc.sdk_version')
    cache_enabled = craftr.session.config.get('msvc.cache', True)

    cache = None
    if cache_enabled:
      try:
        with contextlib.suppress(FileNotFoundError):
          cache = cls.from_file(cls.CACHEFILE())
      except json.JSONDecodeError as e:
        print('warning: could not load MsvcToolkit cache ({}): {}'
          .format(cls.CACHEFILE(), e))

    key_info = (version, arch, platform_type, sdk_version)
    if not cache or cache.key_info != key_info:
      toolkit = cls.from_installation(install, arch, platform_type, sdk_version)
      if cache_enabled:
        toolkit.save(cls.CACHEFILE())
    else:
      toolkit = cache  # Nothing has changed

    if cache_enabled:
      craftr.session.on('after_load', lambda: toolkit.save(cls.CACHEFILE()))

    return toolkit

  def save(self, file):
    if isinstance(file, str):
      path.makedirs(path.dir(file))
      with open(file, 'w') as fp:
        return self.save(fp)
    json.dump(self.asdict(), file, cls=AsDictJSONEncoder)

  @property
  def key_info(self):
    return (self.version, self.arch, self.platform_type, self.sdk_version)

  @property
  def csc_version(self):
    if not self._csc_version:
      with sh.override_environ(self.environ):
        try:
          output = subprocess.check_output(['csc', '/version'], stderr=subprocess.STDOUT).decode()
        except subprocess.CalledProcessError as e:
          # Older versions of CSC don't support the /version flag.
          match = self.CSC_VERSION_REGEX.search(e.stdout.decode())
          if not match:
            raise
          output = match.group(1)
        self._csc_version = output.strip()
    return self._csc_version

  @property
  def cl_version(self):
    return self.cl_info.version

  @property
  def cl_info(self):
    if not self._cl_info:
      self._cl_info = ClInfo.from_program('cl', self.environ)
    return self._cl_info

  @property
  def vbc_version(self):
    if not self._vbc_version:
      with sh.override_environ(self.environ):
        output = subprocess.check_output(['vbc', '/version']).decode()
        self._vbc_version = output.strip()
    return self._vbc_version

  @classmethod
  @functools.lru_cache()
  def get(cls):
    toolkit = cls.from_config()
    print('MSVC v{}-{} ({})'.format(
      toolkit.version, toolkit.arch, toolkit.directory))
    return toolkit


def main():
  if not MsvcInstallation.list():
    print('no MSVC installations could be detected.', file=sys.stderr)
    sys.exit(1)
  for inst in MsvcInstallation.list():
    print('- %4d: %s' % (inst.version, inst.directory))


if require.main == module:
  main()

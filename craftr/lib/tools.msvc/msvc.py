"""
Detect MSVC installations on the current system (Windows only).
"""

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
import logging as log

from craftr import path, sh, utils
batchvars = load('tools.batchvars').batchvars


class MsvcInstallation(utils.named):
  """
  Represents an MSVC installation directory.
  """

  _list = None
  __annotations__ = [
    ('version', int),
    ('directory', str),
    ('_environ', dict, None),
  ]

  @property
  def vcvarsall(self):
    """
    Generates the path to the `vcvarsall.bat`.
    """

    if self.version >= 141:
      return os.path.join(self.directory, 'VC', 'Auxiliary', 'Build', 'vcvarsall.bat')
    else:
      return os.path.join(self.directory, 'VC', 'vcvarsall.bat')

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

    if self._environ is not None:
      return self._environ

    arch = options.arch
    if arch == 'x86_64':
      arch = 'x86_amd64'

    args = [arch]
    if platform_type:
      args.append(platform_type)
    if sdk_version:
      args.append(sdk_version)
    return batchvars(self.vcvarsall, *args)

  @classmethod
  def list(cls):
    """
    List all available MSVC installations.
    """

    if cls._list is not None:
      return cls._list

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
    if 141 not in have_versions:
      programfiles = os.getenv('ProgramFiles(x86)', '') or os.getenv('ProgramFiles', '')
      if programfiles:
        vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Community')
        if not os.path.isdir(vspath):
          vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Professional')
        if not os.path.isdir(vspath):
          vspath = os.path.join(programfiles, 'Microsoft Visual Studio\\2017\\Enterprise')
        if os.path.isdir(vspath):
          results.append(cls(141, vspath))

    # TODO: Special handling for newer MSVC versions?

    result = sorted(results, key=operator.attrgetter('version'), reverse=True)

    # Special handling for explicitly defined MSVC install directory.
    if options.installDir:
      if not os.path.exists(options.installDir):
        log.warn('msvc.install_dir={!r} does not exist'.format(options.installDir))
      else:
        result.insert(0, cls(-1, options.installDir))

    cls._list = result
    return cls._list


class AsDictJSONEncoder(json.JSONEncoder):

  def default(self, obj):
    if hasattr(obj, '_asdict'):
      return obj._asdict()
    elif hasattr(obj, 'asdict'):
      return obj.asdict()
    return super().default(obj)


class ClInfo(utils.named):

  __annotations__ = [
    ('version', str),
    ('version_str', str),
    ('target', str),  # Either x86 or x64
    ('msvc_deps_prefix', str, None),
    ('assembler_program', str),
    ('link_program', str),
    ('lib_program', str)
  ]

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


class MsvcToolkit(utils.named):
  """
  Similar to a #MsvcInstallation, this class represents an MSVC
  installation, however it is fixed to a specific target architecture and
  Windows SDK, etc. Additionally, it can be saved to and loaded from disk.
  """

  CSC_VERSION_REGEX = re.compile(r'compiler\s+version\s+([\d\.]+)', re.I | re.M)

  __annotations__ = [
    ('version', int),
    ('directory', str),
    ('environ', dict, None),
    ('arch', str, None),
    ('platform_type', str, None),
    ('sdk_version', str, None),
    ('_csc_version', str, None),
    ('_vbc_version', str, None),
    ('_cl_info', ClInfo, None),
    ('_deps_prefix', str, None)
  ]

  @classmethod
  def from_installation(cls, inst, arch=None, platform_type=None, sdk_version=None):
    environ = inst.environ(arch, platform_type, sdk_version)
    return cls(inst.version, inst.directory, environ, arch, platform_type, sdk_version)

  @classmethod
  def fromdict(cls, data):
    if data.get('_cl_info'):
      data['_cl_info'] = ClInfo(**data['_cl_info'])
    return cls(**data)

  @classmethod
  @functools.lru_cache()
  def from_config(cls):
    installations = MsvcInstallation.list()
    if not installations:
      raise RuntimeError('Unable to detect any MSVC installation. Is it installed?')

    version = options.version
    if version:
      version = int(version)
      install = next((x for x in installations if x.version == version), None)
      if not install:
        raise RuntimeError('MSVC version "{}" is not available.'.format(version))
    else:
      install = installations[0]
      version = install.version

    arch = options.arch
    platform_type = options.platformType
    sdk_version = options.sdkVersion

    cache = None
    if 'msvc.cache' in context.cache:
      cache = cls.fromdict(context.cache['msvc.cache'])

    key_info = (version, arch, platform_type, sdk_version)
    if not cache or cache.key_info != key_info:
      toolkit = cls.from_installation(install, arch, platform_type, sdk_version)
      context.cache['msvc.cache'] = toolkit.asdict()
    else:
      toolkit = cache  # Nothing has changed

    return toolkit

  @property
  def key_info(self):
    return (self.version, self.arch, self.platform_type, self.sdk_version)

  @property
  def vs_year(self):
    if self.version == 90: return 2008
    elif self.version == 100: return 2010
    elif self.version == 110: return 2012
    elif self.version == 120: return 2013
    elif self.version == 140: return 2015
    elif self.version == 141: return 2017
    else: raise ValueError('unknown MSVC version: {!r}'.format(self.version))

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

  @property
  def deps_prefix(self):
    """
    Returns the string that is the prefix for the `/showIncludes` option
    in the `cl` command.
    """

    if self._deps_prefix:
      return self._deps_prefix

    # Determine the msvc_deps_prefix by making a small test. The
    # compilation will not succeed since no entry point is defined.
    deps_prefix = None
    with utils.tempfile(suffix='.cpp', text=True) as fp:
      fp.write('#include <stddef.h>\n')
      fp.close()
      command = ['cl', '/Zs', '/showIncludes', fp.name, '/nologo']
      try:
        with sh.override_environ(self.environ):
          output = sh.check_output(command).decode()
      except OSError as exc:
        deps_prefix = None
      else:
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
              raise EnvironmentError(msg.format(program, output))
            match = re.search('[\w\s]+:[\w\s]+:', line)
            if match:
              deps_prefix = match.group(0)
      finally:
        os.remove(fp.name)

    if not deps_prefix:
      print('warn: unable to determine MSVC deps prefix')

    self._deps_prefix = deps_prefix
    return deps_prefix

  @classmethod
  @functools.lru_cache()
  def get(cls):
    toolkit = cls.from_config()
    log.info('MSVC v{}-{} ({})'.format(
      toolkit.version, toolkit.arch, toolkit.directory))
    return toolkit


def main(argv=None):
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('--json', action='store_true', help='Output in JSON format.')
  parser.add_argument('argv', nargs='...')
  args = parser.parse_args(argv)

  installs = MsvcInstallation.list()
  if args.argv:
    with sh.override_environ(installs[0].environ()):
      return subprocess.call(args.argv)

  if args.json:
    result = {}
    for inst in installs:
      result[inst.version] = inst.directory
    print(json.dumps(result, indent=2))
  else:
    if not installs:
      log.error('no MSVC installations could be detected.')
      return 1
    for inst in installs:
      tk = MsvcToolkit.from_installation(inst)
      print('- {}: {}'.format(inst.version, inst.directory))
      print('  cl Version: {}'.format(tk.cl_info.version))
      print()
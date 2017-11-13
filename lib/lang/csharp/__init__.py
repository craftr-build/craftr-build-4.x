"""
Targets for building C# projects.
"""

import functools
import os
import re
import requests
import subprocess
import sys
import typing as t
import craftr from '../../public'
import msvc from '../msvc'
import path from '../../utils/path'
import sh from '../../utils/sh'
import log from '../../utils/log'
import {NamedObject} from '../../utils/types'

if os.name == 'nt':
  platform = 'windows'
else:
  platform = sys.platform

artifacts_dir = path.join(craftr.session.builddir, '.nuget-artifacts')


class CscInfo(NamedObject):
  impl: str
  program: t.List[str]
  environ: dict
  version: str
  netversion: str = 'net45'  # XXX determine default netversion here

  def __repr__(self):
    return '<CscInfo impl={!r} program={!r} environ=... version={!r}>'\
      .format(self.impl, self.program, self.version)

  def is_mono(self):
    assert self.impl in ('net', 'mono'), self.impl
    return self.impl == 'mono'

  def exec_args(self, argv):
    if self.is_mono():
      return ['mono'] + argv
    return argv

  def get_nuget(self):
    """
    Checks if the `nuget` command-line program is available, and otherwise
    downloads it into the artifact directory.
    """

    local_nuget = path.join(artifacts_dir, 'nuget.exe')
    if not os.path.isfile(local_nuget):
      if sh.which('nuget') is not None:
        return ['nuget']
      log.info('[Downloading] NuGet ({})'.format(local_nuget))
      response = requests.get('https://dist.nuget.org/win-x86-commandline/latest/nuget.exe')
      response.raise_for_status()
      path.makedirs(artifacts_dir, exist_ok=True)
      with open(local_nuget, 'wb') as fp:
        for chunk in response.iter_content():
          fp.write(chunk)
      path.chmod(local_nuget, '+x')
    return self.exec_args([path.abs(local_nuget)])

  def get_merge_tool(self, out, primary, assemblies=()):
    """
    Checks if the `ILMerge` or `ILRepack` command-line program is available, and
    otherwise installs it using NuGet into the artifact directory.
    """

    tool = craftr.session.config.get('csharp.merge_tool')
    if not tool:
      if self.is_mono():
        tool = 'ILRepack:2.0.13'
      else:
        tool = 'ILMerge:2.14.1208'

    tool_name, version = tool.partition(':')[::2]
    local_tool = path.join(artifacts_dir, tool_name + '.' + version, 'tools', tool_name + '.exe')
    command = None
    if not os.path.isfile(local_tool):
      if sh.which(tool_name) is not None:
        command = [tool_name]
      else:
        install_cmd = self.get_nuget() + ['install', tool_name, '-Version', version]
        log.info('[Installing] {}.{}'.format(tool_name, version))
        path.makedirs(artifacts_dir, exist_ok=True)
        subprocess.run(install_cmd, check=True, cwd=artifacts_dir)
    if not command:
      command = self.exec_args([path.abs(local_tool)])

    return command + ['/out:' + out] + [primary] + list(assemblies)

  @staticmethod
  @functools.lru_cache()
  def get():
    impl = craftr.session.config.get('csharp.impl', 'net' if platform == 'windows' else 'mono')
    if impl not in ('net', 'mono'):
      raise ValueError('unsupported csharp.impl={!r}'.format(impl))

    program = craftr.session.config.get('csharp.csc', 'csc')
    is_mcs = path.rmvsuffix(program).lower().endswith('mcs')

    if impl == 'net':
      toolkit = msvc.MsvcToolkit.get()
      csc = CscInfo(impl, [program], toolkit.environ, toolkit.csc_version)
    else:
      environ = {}
      if platform == 'windows':
        # Also, just make sure that we can find some standard installation
        # of Mono.
        arch = craftr.session.config.get('csharp.mono_arch', None)
        monobin_x64 = path.join(os.getenv('ProgramFiles'), 'Mono', 'bin')
        monobin_x86 = path.join(os.getenv('ProgramFiles(x86)'), 'Mono', 'bin')
        if arch is None:
          if os.path.isdir(monobin_x64):
            monobin = monobin_x64
          else:
            monobin = monobin_x86
        elif arch == 'x64':
          monobin = monobin_x64
        elif arch == 'x86':
          monobin = monobin_x86
        else:
          raise ValueError('invalid value csharp.mono_arch={!r}'.format(arch))
        environ['PATH'] = monobin + path.pathsep + os.getenv('PATH')

        # On windows, the mono compiler is available as .bat file, thus we
        # need to run it through the shell.
        program = sh.shellify([program])
      else:
        program = [program]

      if is_mcs:
        with sh.override_environ(environ):
          version = subprocess.check_output(program + ['--version']).decode().strip()
        m = re.search('compiler\s+version\s+([\d\.]+)', version)
        if not m:
          raise ValueError('Mono compiler version could not be detected from:\n\n  ' + version)
        version = m.group(1)
      else:
        with sh.override_environ(environ):
          version = subprocess.check_output(program + ['/version']).decode().strip()

      csc = CscInfo(impl, program, environ, version)

    print('{} v{}'.format('CSC' if csc.impl == 'net' else csc.impl, csc.version))
    return csc


class Csharp(craftr.target.TargetData):

  # TODO: More features for the C# target.
  #platform: str = None
  #win32icon
  #win32res
  #warn
  #checked

  def __init__(self,
               srcs: t.List[str],
               type: str,
               dll_dir: str = None,
               dll_name: str = None,
               main: str = None,
               csc: CscInfo = None,
               extra_arguments: t.List[str] = None,
               merge_assemblies: bool = False):
    assert type in ('appcontainerexe', 'exe', 'library', 'module', 'winexe', 'winmdobj')
    self.srcs = srcs
    self.type = type
    self.dll_dir = dll_dir
    self.dll_name = dll_name
    self.main = main
    self.csc = csc
    self.extra_arguments = extra_arguments
    self.merge_assemblies = merge_assemblies

  def mounted(self, target):
    if self.dll_dir:
      self.dll_dir = canonicalize(self.dll_dir, target.cell.builddir)
    else:
      self.dll_dir = target.cell.builddir
    self.dll_name = self.dll_name or (target.cell.name.split('/')[-1] + '-' + target.name + '-' + target.cell.version)
    self.csc = self.csc or CscInfo.get()

  @property
  def dll_filename(self):
    return self._dll_filename()

  def _dll_filename(self, final=True):
    if self.type in ('appcontainerexe', 'exe', 'winexe'):
      suffix = '.exe'
    elif self.type == 'winmdobj':
      suffix = '.winmdobj'
    elif self.type == 'module':
      suffix = '.netmodule'
    elif self.type == 'library':
      suffix = '.dll'
    else:
      raise ValueError('invalid type: {!r}'.format(self.type))
    result = path.join(self.dll_dir, self.dll_name) + suffix
    if self.merge_assemblies and not final:
      result = path.addtobase(result, '-intermediate')
    return result

  def translate(self, target):
    # XXX Take C# libraries and maybe even other native libraries into account.
    modules = []
    references = []
    for data in target.deps().attr('data'):
      if isinstance(data, Csharp):
        if data.type == 'module':
          modules.append(data.dll_filename)
        else:
          references.append(data.dll_filename)
      elif isinstance(data, CsharpPrebuilt):
        references.extend(data.dll_filenames)

    build_outfile = self._dll_filename(False)
    command = self.csc.program + ['-nologo', '-target:' + self.type]
    command += ['-out:' + build_outfile]
    if self.main:
      command.append('-main:' + self.main)
    if modules:
      command.append('-addmodule:' + ';'.join(modules))
    if references:
      command += ['-reference:' + x for x in references]
    if self.extra_arguments:
      command += self.extra_arguments
    command += self.srcs

    mkdir = craftr.actions.Mkdir.new(
      target,
      name = 'mkdir',
      directory = self.dll_dir
    )
    build = craftr.actions.System.new(
      target,
      name = 'csc',
      deps = [mkdir, ...],
      environ = self.csc.environ,
      commands = [command],
      input_files = self.srcs,
      output_files = [build_outfile]
    )

    if self.merge_assemblies:
      command = self.csc.get_merge_tool(out=self.dll_filename, primary=build_outfile, assemblies=references)
      craftr.actions.System.new(
        target,
        name = 'ilmerge',
        deps = [build],
        environ = self.csc.environ,
        commands = [command],
        input_files = [build_outfile] + references,
        output_files = [self.dll_filename]
      )


class CsharpPrebuilt(craftr.target.TargetData):

  def __init__(self,
               dll_filename: str = None,
               dll_filenames: t.List[str] = None,
               package: str = None,
               packages: t.List[str] = None,
               csc: CscInfo = None):
    if dll_filename:
      dll_filenames = [dll_filenames]
    if package:
      packages = [package]

    self.packages_install_dir = None
    self.packages = []
    self.dll_filenames = list(dll_filenames or [])
    self.csc = csc or CscInfo.get()

    if packages:
      self.packages_install_dir = artifacts_dir
      for pkg in packages:
        name, version = pkg.partition(':')[::2]
        version, netversion = version.partition('#')[::2]
        if not netversion:
          netversion = self.csc.netversion
        # XXX Determine the .NET target version, not just default to net40.
        package_dir = path.join(self.packages_install_dir, name + '.' + version)
        libname = path.join(package_dir, 'lib', netversion, name + '.dll')
        self.packages.append((name, version, package_dir))
        self.dll_filenames.append(libname)
    else:
      self.dll_filenames.extend(dll_filenames)

  def translate(self, target):
    if not self.packages:
      return

    mkdir = craftr.actions.Mkdir.new(target, directory = self.packages_install_dir)
    for name, version, package_dir in self.packages:
      command = self.csc.get_nuget() + ['install', name, '-Version', version]
      craftr.actions.System.new(
        target,
        name = '{}.{}'.format(name, version),
        commands = [command],
        deps = [mkdir, ...],
        output_files = [package_dir],
        cwd = self.packages_install_dir
      )


def run(binary, *argv, name=None, csc=None, **kwargs):
  kwargs.setdefault('explicit', True)
  target = craftr.T(binary)
  if name is None:
    name = target.name + '_run'
  if csc is None:
    csc = target.data.csc
  command = csc.exec_args([target.data.dll_filename] + list(argv))
  return craftr.gentarget(name = name, deps = [target], commands = [command],
    environ=csc.environ, **kwargs)


build = craftr.target_factory(Csharp)
prebuilt = craftr.target_factory(CsharpPrebuilt)

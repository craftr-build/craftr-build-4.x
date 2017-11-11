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


def get_nuget():
  """
  Checks if the `nuget` command-line program is available, and otherwise
  downloads it into the artifact directory.
  """

  local_nuget = path.join(artifacts_dir, 'nuget.exe')
  if not os.path.isfile(local_nuget):
    if sh.which('nuget') is not None:
      return 'nuget'
    log.info('[Downloading] NuGet ({})'.format(local_nuget))
    response = requests.get('https://dist.nuget.org/win-x86-commandline/latest/nuget.exe')
    response.raise_for_status()
    path.makedirs(artifacts_dir, exist_ok=True)
    with open(local_nuget, 'wb') as fp:
      for chunk in response.iter_content():
        fp.write(chunk)
    path.chmod(local_nuget, '+x')
  return local_nuget


def get_ilmerge(csc, version='2.14.1208'):
  """
  Checks if the `ILMerge` command-line program is available, and otherwise
  installs it using NuGet into the artifact directory.
  """

  local_ilmerge = path.join(artifacts_dir, 'ILMerge.' + version, 'tools', 'ILMerge.exe')
  if not os.path.isfile(local_ilmerge):
    if sh.which('ILMerge') is not None:
      return 'ILMerge'
    install_cmd = [get_nuget(), 'install', 'ILMerge', '-Version', version]
    log.info('[Installing] ILMerge.' + version)
    subprocess.run(csc.exec_args(install_cmd), check=True, cwd=artifacts_dir)
  return local_ilmerge


class CscInfo(NamedObject):
  impl: str
  program: t.List[str]
  environ: dict
  version: str

  def __repr__(self):
    return '<CscInfo impl={!r} program={!r} environ=... version={!r}>'\
      .format(self.impl, self.program, self.version)

  def is_mono(self):
    # TODO: That's pretty dirty..
    return self.program != ['csc']

  def exec_args(self, argv):
    if self.is_mono():
      return ['mono'] + argv
    return argv

  @staticmethod
  @functools.lru_cache()
  def get():
    impl = craftr.session.config.get('csharp.impl', 'net' if platform == 'windows' else 'mono')
    if impl not in ('net', 'mono'):
      raise ValueError('unsupported csharp.impl={!r}'.format(impl))

    program = craftr.session.config.get('csharp.csc')
    if impl == 'net' and program:
      raise ValueError('csharp.csc not supported with csharp.impl={!r}'.format(impl))
    elif impl == 'net':
      program = 'csc'
    elif impl == 'mono':
      program = 'mcs'
    else: assert False

    program = sh.split(program)
    if impl == 'net':
      toolkit = msvc.MsvcToolkit.get()
      csc = CscInfo(impl, program, toolkit.environ, toolkit.csc_version)
    else:
      environ = {}
      if platform == 'windows':
        # On windows, the mono compiler is available as .bat file, thus we
        # need to run it through the shell.
        program = sh.shellify(program)
        # Also, just make sure that we can find some standard installation
        # of Mono.
        if match(arch, '*64'):
          monobin = path.join(os.getenv('ProgramFiles'), 'Mono', 'bin')
        else:
          monobin = path.join(os.getenv('ProgramFiles(x86)'), 'Mono', 'bin')
        environ['PATH'] = os.getenv('PATH') + path.pathsep + monobin

      # TODO: Cache the compiler version (like the MsvcToolkit does).
      with sh.override_environ(environ):
        version = subprocess.check_output(program + ['--version']).decode().strip()
      if impl == 'mono':
        m = re.search('compiler\s+version\s+([\d\.]+)', version)
        if not m:
          raise ValueError('Mono compiler version could not be detected from:\n\n  ' + version)
        version = m.group(1)

      csc = CscInfo(impl, program, environ, version)

    print('CSC v{}'.format(csc.version))
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
        references.append(data.dll_filename)

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
      command = [get_ilmerge(self.csc)]
      command += ['/out:' + self.dll_filename] + [build_outfile] + references
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

  def __init__(self, dll_filename: str = None, package: str = None, csc: CscInfo = None):
    if package and dll_filename:
      raise ValueError('dll_filename and package arguments may not be '
          'specified at the same time.')
    if package:
      self.package_name, self.package_version = package.partition(':')[::2]
      self.install_dir = artifacts_dir
      self.package_dir = path.join(self.install_dir, '{}.{}'.format(
          self.package_name, self.package_version))
      # XXX dll_filename?? How to find the right one.
      self.dll_filename = path.join(self.package_dir, 'lib', 'net40', self.package_name + '.dll')
    else:
      self.package_name = self.package_version = None
      self.install_dir = None
      self.package_dir = None
      self.dll_filename = craftr.localpath(dll_filename)
    self.csc = csc or CscInfo.get()

  def translate(self, target):
    if not self.package_name:
      return
    command = [get_nuget(), 'install', self.package_name, '-Version', self.package_version]
    command = self.csc.exec_args(command)
    mkdir = craftr.actions.Mkdir.new(
      target,
      directory = self.install_dir
    )
    craftr.actions.System.new(
      target,
      commands = [command],
      deps = [mkdir, ...],
      output_files = [self.package_dir],
      cwd = self.install_dir
    )


def run(binary, *argv, name=None, csc=None, **kwargs):
  kwargs.setdefault('explicit', True)
  target = craftr.T(binary)
  if name is None:
    name = target.name + '_run'
  if csc is None:
    csc = target.data.csc
  command = csc.exec_args([target.data.dll_filename] + list(argv))
  return craftr.gentarget(name = name, deps = [target], commands = [command], **kwargs)


build = craftr.target_factory(Csharp)
prebuilt = craftr.target_factory(CsharpPrebuilt)

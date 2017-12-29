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
import craftr, {options} from 'craftr'
import msvc from 'craftr/tools/msvc'
import path from 'craftr/utils/path'
import sh from 'craftr/utils/sh'
import utils from 'craftr/utils'
import nupkg from './nupkg'

import logging as log

if os.name == 'nt':
  platform = 'windows'
else:
  platform = sys.platform

artifacts_dir = path.join(craftr.build_directory, '.nuget-artifacts')


class CscInfo(utils.named):

  __annotations__ = [
    ('impl', str),
    ('program', t.List[str]),
    ('environ', dict),
    ('version', str),
    ('netversion', str, 'net45')  # XXX determine default netversion here
  ]

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

    tool = options.get('csharp.merge_tool')
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
        subprocess.check_call(install_cmd, cwd=artifacts_dir)

    if not command:
      command = self.exec_args([path.abs(local_tool)])

    return command + ['/out:' + out] + [primary] + list(assemblies)

  @staticmethod
  @functools.lru_cache()
  def get():
    impl = options.get('csharp.impl', 'net' if platform == 'windows' else 'mono')
    if impl not in ('net', 'mono'):
      raise ValueError('unsupported csharp.impl={!r}'.format(impl))

    program = options.get('csharp.csc', 'csc')
    is_mcs = path.rmvsuffix(program).lower().endswith('mcs')

    if impl == 'net':
      toolkit = msvc.MsvcToolkit.get()
      csc = CscInfo(impl, [program], toolkit.environ, toolkit.csc_version)
    else:
      environ = {}
      if platform == 'windows':
        # Also, just make sure that we can find some standard installation
        # of Mono.
        arch = options.get('csharp.mono_arch', None)
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

    log.info('{} v{}'.format('CSC' if csc.impl == 'net' else csc.impl, csc.version))
    return csc


class CsharpBuild(craftr.Behaviour):

  # TODO: More features for the C# target.
  #platform: str = None
  #win32icon
  #win32res
  #warn
  #checked

  def init(self, srcs, type, dll_dir=None, dll_name=None, main=None, csc=None,
           extra_arguments=None, merge_assemblies=False):
    assert type in ('appcontainerexe', 'exe', 'library', 'module', 'winexe', 'winmdobj')
    self.srcs = srcs
    self.type = type
    self.dll_dir = dll_dir
    self.dll_name = dll_name
    self.main = main
    self.csc = csc
    self.extra_arguments = extra_arguments
    self.merge_assemblies = merge_assemblies
    if self.dll_dir:
      self.dll_dir = canonicalize(self.dll_dir, self.namespace.build_directory)
    else:
      self.dll_dir = self.namespace.build_directory
    self.dll_name = self.dll_name or (self.namespace.name.split('/')[-1] + '-' + self.target.name + '-' + self.namespace.version)
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

  def translate(self):
    # XXX Take C# libraries and maybe even other native libraries into account.
    modules = []
    references = []
    for target in self.target.deps(with_behaviour=CsharpBuild):
      if target.impl.type == 'module':
        modules.append(target.impl.dll_filename)
      else:
        references.append(target.impl.dll_filename)
    for target in self.target.deps(with_behaviour=CsharpPrebuilt):
      references.extend(target.impl.dll_filenames)

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

    self.target.add_action(
      name = 'csc',
      environ = self.csc.environ,
      commands = [command],
      input_files = self.srcs,
      output_files = [build_outfile]
    )

    if self.merge_assemblies:
      command = self.csc.get_merge_tool(out=self.dll_filename, primary=build_outfile, assemblies=references)
      self.target.add_action(
        name = 'ilmerge',
        environ = self.csc.environ,
        commands = [command],
        input_files = [build_outfile] + references,
        output_files = [self.dll_filename]
      )


class CsharpPrebuilt(craftr.Behaviour):

  def init(self, dll_filenames=None, packages=None, csc=None):
    self.packages_install_dir = artifacts_dir
    self.packages = [nupkg.Dependency.from_str(x) for x in (packages or [])]
    self.dll_filenames = [craftr.localpath(x) for x in (dll_filenames or [])]
    self.csc = csc or CscInfo.get()

  def install(self):
    """
    Installs the NuGet packages and appends all libraries to the
    #dll_filenames member.
    """

    deps = set()

    path.makedirs(self.packages_install_dir, exist_ok=True)
    for dep in self.packages:
      deps.add(dep)

      # Only install if the .nupkg file does not already exists.
      nupkg_file = dep.nupkg(self.packages_install_dir)
      if not path.isfile(nupkg_file):
        command = self.csc.get_nuget() + ['install', dep.id, '-Version', dep.version]
        subprocess.check_call(command, cwd=self.packages_install_dir)

      # Parse the .nuspec for this package's dependencies.
      specdom = nupkg.get_nuspec(nupkg_file)
      if not specdom:
        log.warn('Could not read .nuspec from "{}"'.format(nupkg_file))
        continue

      # XXX determine target_framework, None includes ALL dependencies (which is bad)
      target_framework = None
      for dep in nupkg.nuspec_eval_deps(specdom, target_framework):
        deps.add(dep)

    for dep in deps:
      filename = dep.resolve(self.packages_install_dir, framework=self.csc.netversion)
      if filename is not None:
        self.dll_filenames.append(filename)

  def translate(self):
    self.install()


def run(binary, *argv, name=None, csc=None, **kwargs):
  kwargs.setdefault('explicit', True)
  target = craftr.resolve_target(binary)
  if name is None:
    name = target.name + '_run'
  if csc is None:
    csc = target.impl.csc
  command = csc.exec_args([target.impl.dll_filename] + list(argv))
  return craftr.gentarget(name = name, deps = [target], commands = [command],
    environ=csc.environ, **kwargs)


build = craftr.Factory(CsharpBuild)
prebuilt = craftr.Factory(CsharpPrebuilt)

"""
Targets for building C# projects.
"""

import functools
import os
import re
import subprocess
import sys
import typing as t
import craftr from '../public'
import msvc from './msvc'
import path from '../utils/path'
import sh from '../utils/sh'
import {NamedObject} from '../utils/types'

if os.name == 'nt':
  platform = 'windows'
else:
  platform = sys.platform


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

  def __init__(self, srcs: t.List[str], type: str, dll_dir: str = None,
               dll_name: str = None, main: str = None, csc: CscInfo = None,
               extra_arguments: t.List[str] = None):
    assert type in ('appcontainerexe', 'exe', 'library', 'module', 'winexe', 'winmdobj')
    self.srcs = srcs
    self.type = type
    self.dll_dir = dll_dir
    self.dll_name = dll_name
    self.main = main
    self.csc = csc
    self.extra_arguments = extra_arguments

  def mounted(self, target):
    if self.dll_dir:
      self.dll_dir = canonicalize(self.dll_dir, target.cell.builddir)
    else:
      self.dll_dir = target.cell.builddir
    self.dll_name = self.dll_name or (target.cell.name.split('/')[-1] + '-' + target.name + '-' + target.cell.version)
    self.csc = self.csc or CscInfo.get()

  @property
  def dll_filename(self):
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
    return path.join(self.dll_dir, self.dll_name) + suffix

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

    command = self.csc.program + ['-nologo', '-target:' + self.type]
    command += ['-out:' + self.dll_filename]
    if self.main:
      command.append('-main:' + self.main)
    if modules:
      command.append('-addmodule:' + ';'.join(modules))
    if references:
      command += ['-reference:' + x for x in reference]
    if self.extra_arguments:
      command += self.extra_arguments
    command += self.srcs

    mkdir = craftr.actions.Mkdir.new(
      target,
      name = 'mkdir',
      directory = self.dll_dir
    )
    craftr.actions.System.new(
      target,
      name = 'csc',
      deps = [mkdir, ...],
      environ = self.csc.environ,
      commands = [command],
      input_files = self.srcs,
      output_files = [self.dll_filename]
    )


class CsharpRun(craftr.target.TargetData):
  """
  At least under Windows+Mono, applications compiled with Mono should be run
  through the Mono bootstrapper.
  """

  environ: t.Dict[str, str] = None
  cwd: str = None
  extra_arguments: t.List[str] = None
  csc:  CscInfo = None

  def __init__(self, executable: str = None, environ: t.Dict[str, str] = None,
               cwd: str = None, csc: CscInfo = None,
               extra_arguments: t.List[str] = None):
    self.executable = executable
    self.environ = environ
    self.cwd = cwd
    self.csc = csc
    self.extra_arguments = extra_arguments

  def mounted(self, target):
    if not self.executable:
      for data in target.deps().attr('data'):
        if isinstance(data, Csharp) and 'exe' in data.type:
          if self.executable:
            raise ValueError('mulitple executable Csharp dependencies, '
              'specify the one to run explicitly via `executable=...`')
          self.executable = data.dll_filename
        # Inherit the CSC value from the dependency.
        if isinstance(data, Csharp) and not self.csc:
          self.csc = data.csc
      if not self.executable:
        raise ValueError('specify one Csharp executable dependency or the '
          '`executable=...` parameter.')

    self.csc = self.csc or CscInfo.get()
    environ = self.environ.copy() if self.environ else {}
    environ.update(self.csc.environ)  # XXX What if eg. PATH is specified in self.environ?
    self.environ = environ

  def translate(self, target):
    if self.csc.is_mono():
      command = ['mono']
    else:
      command = []
    command += [self.executable]
    if self.extra_arguments:
      command += self.extra_arguments

    craftr.actions.System.new(
      target,
      name = 'run',
      input_files = [self.executable],
      output_files = [],
      commands = [command],
      environ = self.environ,
      cwd = self.cwd
    )


build = craftr.target_factory(Csharp)
run = craftr.target_factory(CsharpRun)

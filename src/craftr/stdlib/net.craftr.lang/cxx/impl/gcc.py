
import sys
import base from './base'
import {get_gcc_info} from 'net.craftr.compiler.mingw'
import {options} from '../build'

from craftr.api import *


class GccCompiler(base.Compiler):

  id = 'gcc'
  name = 'gcc'

  def __init__(self, cross_prefix='', **kwargs):
    for k, v in (('compiler_c', 'gcc'), ('compiler_cpp', 'g++'), ('linker_c', 'gcc'), ('linker_cpp', 'g++')):
      if not getattr(self, k, None):
        setattr(self, k, kwargs.pop(k, v))
      if cross_prefix:
        setattr(self, k, cross_prefix + getattr(self, k))
    if 'arch' not in kwargs or 'version' not in kwargs:
      info = get_gcc_info(self.compiler_c, self.compiler_env or kwargs.get('compiler_env'))
      kwargs.setdefault('arch', 'x64' if '64' in info['target'] else 'x86')
      kwargs.setdefault('version', info['version'])
    super().__init__(**kwargs)

  compiler_c = 'gcc'
  compiler_cpp = 'g++'
  compiler_env = None
  compiler_out = ['-c', '-o', '${@obj}']

  c_std = '-std=%ARG%'
  c_stdlib = '-stdlib=%ARG%'
  cpp_std = '-std=%ARG%'
  cpp_stdlib = '-stdlib=%ARG%'
  pic_flag = '-fPIC'
  debug_flag = '-g'
  define_flag = '-D%ARG%'
  include_flag = '-I%ARG%'
  expand_flag = '-E'
  warnings_flag = []  # TODO: -Wall by default?
  warnings_as_errors_flag = '-Werror'
  optimize_none_flag = '-Od'
  optimize_speed_flag = '-O3'
  optimize_size_flag = '-Os'
  enable_exceptions = []
  disable_exceptions = '-fno-exceptions'
  enable_rtti = []
  disable_rtti = '-fno-rtti'
  force_include = ['-include', '%ARG%']
  save_temps = '-save-temps'
  depfile_args = ['-MMD', '-MF', '${@obj}.d']
  depfile_name = '${@obj}.d'

  compiler_supports_openmp = True
  compiler_enable_openmp = ['-fopenmp']
  linker_enable_openmp = ['-lgomp']

  linker_env = None
  linker_out = ['-o', '%ARG%']
  linker_shared = [pic_flag, '-shared']
  linker_exe = []
  linker_lib = '-l%ARG%'
  linker_libpath = '-L%ARG%'
  linker_runtime = {
    'c': {'static': '-static-libgcc', 'dynamic': []},
    'cpp': {'static': '-static-libstdc++', 'dynamic': []}
  }

  archiver = ['ar', 'rcs']
  archiver_env = None
  archiver_out = '%ARG%'

  def init(self):
    options.add('enableGcov', bool, False)
    if OS.id == 'darwin':
      session.target_props.add('cxx.osxInstallNameTool', 'StringList')

  def get_compile_command(self, target, data, lang):
    flags = super().get_compile_command(target, data, lang)
    if options.enableGcov:
      flags += ['-fprofile-arcs', '-ftest-coverage']
    return flags

  def get_link_command(self, target, data, lang):
    flags = super().get_link_command(target, data, lang)
    if options.enableGcov:
      flags += ['-lgcov']
    if data.defaultSystemLibraries and OS.id == 'linux':
      flags += ['-lm', '-lpthread']
    return flags

  def get_link_commands(self, target, data, lang):
    commands = super().get_link_commands(target, data, lang)
    if OS.id == 'darwin' and data.osxInstallNameTool:
      commands.append(['install_name_tool'] + data.osxInstallNameTool + ['${@product}'])
    return commands

  def on_completion(self, target, data):
    if options.enableGcov and data.type == 'executable':
      commands = [
        [data.productFilename],
        ['gcov', '${<objs}', '-n']
      ]
      operator('cxx.gcov', commands=commands, syncio=True, explicit=True,
        environ=self.compiler_env, cwd=data.runCwd)
      build_set({'objs': data.outObjFiles, 'in': data.productFilename}, {})


def get_compiler(fragment, compiler_class=GccCompiler):
  # TODO: Parse fragment to allow different compiler version
  #       or cross-compiler
  return compiler_class()

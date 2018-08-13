
import sys
import base from './base'
import {get_gcc_info} from 'net.craftr.tool.mingw'

from craftr.api import *


class GccCompiler(base.Compiler):

  id = 'gcc'
  name = 'gcc'

  def __init__(self, cross_prefix='', **kwargs):
    self.compiler_c = self.linker_c = cross_prefix + 'gcc'
    self.compiler_cpp = self.linker_cpp = cross_prefix + 'gcc'
    if 'arch' not in kwargs or 'version' not in kwargs:
      info = get_gcc_info(self.compiler_c, self.compiler_env or kwargs.get('compiler_env'))
      kwargs.setdefault('arch', 'x64' if '64' in info['target'] else 'x86')
      kwargs.setdefault('version', info['version'])
    super().__init__(**kwargs)

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
  depfile_args = ['-MD', '-MP', '-MF', '${@obj}.d']
  depfile_name = '$out.d'  # TODO: This is Ninja syntax, find a way to combine this with the BuildSet variable syntax.

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

  def add_objects_for_source(self, target, data, lang, src, buildset, objdir):
    rel = path.rel(src, target.scope.directory)
    obj = path.setsuffix(path.join(objdir, rel), '.o')
    buildset.add_output_files('obj', [obj])


def get_compiler(fragment, compiler_class=GccCompiler):
  # TODO: Parse fragment to allow different compiler version
  #       or cross-compiler
  return compiler_class()

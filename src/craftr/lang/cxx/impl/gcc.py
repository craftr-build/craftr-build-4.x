
import sys
import base from './base'

from craftr.api import *


class GccCompiler(base.Compiler):

  id = 'gcc'
  arch = 'x64' if sys.maxsize > (2**32-1) else 'x86'  # TOOD: Determine using gcc -v
  name = 'gcc'
  version = '??'  # TODO: Determine using gcc -v

  compiler_env = None
  compiler_c = 'gcc'
  compiler_cpp = 'g++'
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

  linker_c = compiler_c
  linker_cpp = compiler_cpp
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

  executable_suffix = ''
  library_prefix = 'lib'
  library_shared_suffix = '.so'
  library_static_suffix = '.a'

  """
  lib_macro = 'lib$(0)'
  ext_lib_macro = extmacro('.a', '.a.$(0)')
  ext_dll_macro = extmacro('.so', '.so.$(0)')
  ext_exe_macro = extmacro('', '.$(0)')
  obj_macro = '.o'
  """

  def add_objects_for_source(self, target, data, lang, src, buildset, objdir):
    rel = path.rel(src, target.scope.directory)
    obj = path.setsuffix(path.join(objdir, rel), '.o')
    buildset.add_output_files('obj', [obj])


def get_compiler(fragment):
  # TODO: Parse fragment to allow different compiler version
  #       or cross-compiler
  return GccCompiler()

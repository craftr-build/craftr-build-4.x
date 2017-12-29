
from typing import List
import logging as log
import craftr from 'craftr'
import path from 'craftr/utils/path'
import {CompilerOptions, Compiler, extmacro} from '.'


class GccCompilerOptions(CompilerOptions):

  __annotations__ = [
    ('gcc_static_runtime', bool)
  ]


class GccCompiler(Compiler):

  id = 'gcc'
  name = 'gcc'
  version = '??'  # TODO
  options_class = GccCompilerOptions

  compiler_env = None
  compiler_c = 'gcc'
  compiler_cpp = 'g++'
  compiler_out = ['-c', '-o', '$out[0]']

  c_std = '-std=%ARG%'
  cpp_std = '-std=%ARG%'
  pic_flag = '-fPIC'
  debug_flag = '-g'
  define_flag = '-D%ARG%'
  include_flag = '-I%ARG%'
  expand_flag = '-E'
  warnings_flag = []  # TODO: -Wall by default?
  warnings_as_errors_flag = '-Werror'
  optimize_speed_flag = '-O3'
  optimize_size_flag = '-Os'

  linker_c = compiler_c
  linker_cpp = compiler_cpp
  linker_env = None
  linker_out = ['-o', '%ARG%']
  linker_shared = [pic_flag, '-shared']
  linker_exe = []
  linker_lib = '-l%ARG%'
  linker_libpath = '-L%ARG%'

  archiver = ['ar', 'rcs']
  archiver_env = None
  archiver_out = '$out[0]'

  lib_macro = 'lib$(0)'
  ext_lib_macro = extmacro('.a.1', '.a.$(0)')
  ext_dll_macro = extmacro('.so.1', '.so.$(0)')
  ext_exe_macro = extmacro('', '.$(0)')
  obj_macro = '.o'

  gcc_static_libc = '-static-libgcc'
  gcc_static_libstdcpp = '-static-libstdc++'

  def build_link_flags(self, build, outfile, additional_input_files):
    flags = super().build_link_flags(build, outfile, additional_input_files)
    if build.options.gcc_static_runtime and not build.is_staticlib():
      flags += [self.gcc_static_libstdcpp] if build.has_cpp_sources() else [self.gcc_static_libc]
    return flags


def get_compiler(fragment):
  return GccCompiler()

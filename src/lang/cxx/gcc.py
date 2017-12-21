
from typing import List
import logging as log
import craftr from 'craftr'
import path from 'craftr/utils/path'
import base from './base'


class GccCompilerOptions(base.CompilerOptions):
  pass


class GccCompiler(base.Compiler):

  name = 'gcc'
  version = '??'  # TODO
  options_class = GccCompilerOptions

  compiler_env = None
  compiler_c = 'gcc'
  compiler_cpp = 'g++'
  compiler_out = ['-c', '-o', '%ARG%']

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
  archiver_out = '%ARG%'

  lib_macro = 'lib$(0)'
  ext_lib_macro = base.extmacro('.a.1', '.a.$(0)')
  ext_dll_macro = base.extmacro('.so.1', '.so.$(0)')
  ext_exe_macro = base.extmacro('', '.$(0)')
  obj_macro = '.o'


def get_compiler(fragment):
  return GccCompiler()

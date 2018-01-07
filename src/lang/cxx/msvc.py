
from typing import List
import logging as log
import craftr from 'craftr'
import path from 'craftr/utils/path'
import {MsvcToolkit} from 'craftr/tools/msvc'
import {CompilerOptions, Compiler, extmacro} from '.'


class MsvcCompilerOptions(CompilerOptions):

  __annotations__ = [
    ('nodefaultlib', bool, False),
    ('embedd_debug_symbols', bool, True),
    ('msvc_disable_warnings', List[str], None),
    ('msvc_enabled_exceptions', bool, True)
  ]


class MsvcCompiler(Compiler):

  id = 'msvc'
  name = 'msvc'
  options_class = MsvcCompilerOptions

  compiler_c = ['cl', '/nologo']
  compiler_cpp = ['cl', '/nologo']
  compiler_out = ['/c', '/Fo%ARG%']

  c_std = []
  cpp_std = []
  pic_flag = []
  debug_flag = []  # handled explicitly together with embedd_debug_symbols
  define_flag = '/D%ARG%'
  include_flag = '/I%ARG%'
  expand_flag = '/E'
  warnings_flag = '/W4'
  warnings_as_errors_flag = '/WX'
  optimize_speed_flag = '/O2'
  optimize_size_flag = ['/O1', '/Os']

  linker_c = ['link', '/nologo']
  linker_cpp = linker_c
  linker_out = '/OUT:$out[0]'
  linker_shared = '/DLL'
  linker_exe = []
  linker_lib = '%ARG%.lib'
  linker_libpath = '/LIBPATH:%ARG%'
  linker_runtime = {}  # Required flags will be added in build_compile_flags()

  archiver = ['lib', '/nologo']
  archiver_out = '/OUT:$out[0]'

  lib_macro = None
  ext_lib_macro = extmacro('.lib', '.$(0).lib')
  ext_dll_macro = extmacro('.dll', '.$(0).dll')
  ext_exe_macro = extmacro('.exe', '.$(0).exe')
  obj_macro = '.obj'

  def __init__(self, toolkit):
    super().__init__(
      version = toolkit.cl_version,
      arch = toolkit.cl_info.target,
      compiler_env = toolkit.environ,
      linker_env = toolkit.environ,
      archiver_env = toolkit.environ
    )
    self.toolkit = toolkit

  def build_compile_flags(self, build, language):
    command = super().build_compile_flags(build, language)
    options = build.options
    if build.debug:
      command += ['/Od', '/RTC1', '/FC']
      if not self.version or self.version >= '18':
        # Enable parallel writes to .pdb files.
        command += ['/FS']
      if options.embedd_debug_symbols:
        command += ['/Z7']
      else:
        command += ['/Zi', '/Fd' + path.setsuffix(outfile, '.pdb')]
    if options.msvc_disable_warnings:
      command += ['/wd' + str(x) for x in options.msvc_disable_warnings]
    if options.msvc_enabled_exceptions and language == 'cpp':
      command += ['/EHsc']

    if build.static_runtime:
      command += ['/MTd' if build.debug else '/MT']
    else:
      command += ['/MDd' if build.debug else '/MD']

    return command

  def build_link_flags(self, build, outfile, additional_input_files):
    command = super().build_link_flags(build, outfile, additional_input_files)
    options = build.options
    if options.nodefaultlib:
      command += ['/NODEFAULTLIB']
    if build.is_sharedlib():
      command += ['/IMPLIB:$out.lib']  # set from set_target_outputs()
    if build.debug and build.is_sharedlib():
      command += ['/DEBUG']
    return command

  def set_target_outputs(self, build, ctx):
    super().set_target_outputs(build, ctx)
    if build.is_sharedlib():
      build.linkname_full = [path.setsuffix(x, '.lib') for x in build.outname_full]
      build.additional_outputs.append(path.setsuffix(build.outname_full[0], '.exp'))


def get_compiler(fragment):
  if fragment:
    log.warn('craftr/lang/cxx/msvc: Fragment not supported. (fragment = {!r})'
      .format(fragment))
  return MsvcCompiler(MsvcToolkit.from_config())

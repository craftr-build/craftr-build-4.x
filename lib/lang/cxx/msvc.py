
from typing import List
import craftr from 'craftr'
import {log, macro, path} from 'craftr/utils'
import {MsvcToolkit} from 'craftr/toolchains/msvc'
import base from './base'


class MsvcCompilerOptions(base.CompilerOptions):
  nodefaultlib: bool = False
  embedd_debug_symbols: bool = True
  msvc_disable_warnings: List[str] = None
  msvc_enabled_exceptions: bool = True
  msvc_runtime_library: str = None


class MsvcCompiler(base.Compiler):

  name = 'msvc'
  options_class = MsvcCompilerOptions

  compiler_c = ['cl', '/nologo']
  compiler_cpp = ['cl', '/nologo']
  compiler_out = ['/c', '/Fo%ARG%']

  debug_flag = []  # handled explicitly together with embedd_debug_symbols
  define_flag = '/D%ARG%'
  include_flag = '/I%ARG%'
  expand_flag = '/E'
  warnings_flag = '/W4'
  warnings_as_errors_flag = '/WX'
  optimize_speed_flag = '/O2'
  optimize_size_flag = ['/O1', '/Os']

  linker = ['link', '/nologo']
  linker_out = '/OUT:%ARG%'
  linker_shared = '/DLL'
  linker_exe = []
  linker_lib = '%ARG%.lib'
  linker_libpath = '/LIBPATH:%ARG%'

  archiver = ['lib', '/nologo']
  archiver_out = '/OUT:%ARG%'

  lib_macro = None
  ext_lib_macro = staticmethod(base.extmacro('$(0).lib', '.$(0).lib'))
  ext_dll_macro = staticmethod(base.extmacro('$(0).dll', '.$(0).dll'))
  ext_exe_macro = staticmethod(base.extmacro('$(0).exe', '.$(0).exe'))
  obj_macro = '.obj'

  def __init__(self, toolkit):
    super().__init__(
      version = toolkit.cl_version,
      compiler_env = toolkit.environ,
      linker_env = toolkit.environ,
      archiver_env = toolkit.environ
    )
    self.toolkit = toolkit

  def build_compile_flags(self, target, language):
    command = super().build_compile_flags(target, language)
    data = target.data
    options = data.options
    if data.debug:
      command += ['/Od', '/RTC1', '/FC']
      if not self.version or self.version >= '18':
        # Enable parallel writes to .pdb files.
        command += ['/Fs']
      if options.embedd_debug_symbols:
        command += ['/Z7']
      else:
        command += ['/Zi', '/Fd' + path.setsuffix(outfile, '.pdb')]
    if options.msvc_disable_warnings:
      command += ['/wd' + str(x) for x in options.msvc_disable_warnings]
    if options.msvc_enabled_exceptions and language == 'cpp':
      command += ['/EHsc']

    # If not explicitly specified, determine whether we should link the
    # MSVC runtime library statically or dynamically.
    if not options.msvc_runtime_library:
      if data.link_style == 'static':
        options.msvc_runtime_library = 'static'
      elif data.link_style == 'shared':
        options.msvc_runtime_library = 'dynamic'
      else:
        assert False, data.link_style

    if options.msvc_runtime_library == 'static':
      command += ['/MTd' if data.debug else '/MT']
    elif options.msvc_runtime_library == 'dynamic':
      command += ['/MDd' if data.debug else '/MD']
    else:
      assert False, options.msvc_runtime_library

    return command

  def build_link_flags(self, target, outfile, additional_input_files):
    command = super().build_link_flags(target, outfile, additional_input_files)
    data = target.data
    options = data.options
    if options.nodefaultlib:
      command += ['/NODEFAULTLIB']
    if data.is_sharedlib():
      command += ['/IMPLIB:' + data.linkname_full]  # set from set_target_outputs()
    return command

  def set_target_outputs(self, target, ctx):
    super().set_target_outputs(target, ctx)
    if target.data.is_sharedlib():
      target.data.linkname_full = path.setsuffix(target.data.outname_full, '.lib')


def get_compiler(fragment):
  if fragment:
    log.warn('craftr/lang/cxx/msvc: Fragment not supported. (fragment = {!r})'
      .format(fragment))
  return MsvcCompiler(MsvcToolkit.from_config())

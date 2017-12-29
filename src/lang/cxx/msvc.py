
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
    ('msvc_enabled_exceptions', bool, True),
    ('msvc_runtime_library', str, None)
  ]


class MsvcCompiler(Compiler):

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
      compiler_env = toolkit.environ,
      linker_env = toolkit.environ,
      archiver_env = toolkit.environ
    )
    self.toolkit = toolkit

  def build_compile_flags(self, impl, language):
    command = super().build_compile_flags(impl, language)
    options = impl.options
    if impl.debug:
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

    # If not explicitly specified, determine whether we should link the
    # MSVC runtime library statically or dynamically.
    if not options.msvc_runtime_library:
      options.msvc_runtime_library = craftr.options.get('msvc.runtime_library')
    if not options.msvc_runtime_library:
      if impl.link_style == 'static':
        options.msvc_runtime_library = 'static'
      elif impl.link_style == 'shared':
        options.msvc_runtime_library = 'dynamic'
      else:
        assert False, impl.link_style

    if options.msvc_runtime_library == 'static':
      command += ['/MTd' if impl.debug else '/MT']
    elif options.msvc_runtime_library == 'dynamic':
      command += ['/MDd' if impl.debug else '/MD']
    else:
      assert False, options.msvc_runtime_library

    return command

  def build_link_flags(self, impl, outfile, additional_input_files):
    command = super().build_link_flags(impl, outfile, additional_input_files)
    options = impl.options
    if options.nodefaultlib:
      command += ['/NODEFAULTLIB']
    if impl.is_sharedlib():
      command += ['/IMPLIB:$out.lib']  # set from set_target_outputs()
    return command

  def set_target_outputs(self, impl, ctx):
    super().set_target_outputs(impl, ctx)
    if impl.is_sharedlib():
      impl.linkname_full = [path.setsuffix(x, '.lib') for x in impl.outname_full]


def get_compiler(fragment):
  if fragment:
    log.warn('craftr/lang/cxx/msvc: Fragment not supported. (fragment = {!r})'
      .format(fragment))
  return MsvcCompiler(MsvcToolkit.from_config())

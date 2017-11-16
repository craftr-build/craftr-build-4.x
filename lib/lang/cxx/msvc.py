
import craftr from 'craftr'
import {log, macro, path} from 'craftr/utils'
import {MsvcToolkit} from 'craftr/lang/msvc'
import base from './base'


class MsvcCompiler(base.Compiler):

  name = 'msvc'

  compiler_c = ['cl', '/nologo']
  compiler_cpp = ['cl', '/nologo']
  compiler_out = ['/c', '/Fo%ARG%']

  debug_flag = '/Z7'
  define_flag = '/D%ARG%'
  include_flag = '/I%ARG%'
  expand_flag = '/E'
  warnings_flag = '/W4'
  warnings_as_errors_flag = '/WX'

  linker = ['link', '/nologo']
  linker_out = '/OUT:%ARG%'
  linker_shared = '/DLL'
  linker_exe = []

  archiver = ['lib', '/nologo']
  archiver_out = '/OUT:%ARG%'

  lib_macro = None
  ext_lib_macro = '.lib'
  ext_dll_macro = '.dll'
  ext_exe_macro = '.exe'
  obj_macro = '.obj'

  def __init__(self, toolkit):
    super().__init__(
      version = toolkit.cl_version,
      compiler_env = toolkit.environ,
      linker_env = toolkit.environ,
      archiver_env = toolkit.environ
    )
    self.toolkit = toolkit


def get_compiler(fragment):
  if fragment:
    log.warn('craftr/lang/cxx/msvc: Fragment not supported. (fragment = {!r})'
      .format(fragment))
  return MsvcCompiler(MsvcToolkit.from_config())

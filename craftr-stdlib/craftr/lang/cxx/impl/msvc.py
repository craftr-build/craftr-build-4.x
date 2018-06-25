
from typing import Union, List
import logging as log
import nr.fs as path
import nr.stream
import craftr, {BUILD} from 'craftr'
import base from './base'
import msvc from 'craftr/tools/msvc'

unique = nr.stream.stream.unique

"""
class MsvcCompilerOptions(CompilerOptions):

  __annotations__ = [
    ('msvc_nodefaultlib', Union[bool, List[str]], None),
    ('embedd_debug_symbols', bool, True),
    ('msvc_disable_warnings', List[str], None),
    ('msvc_warnings_as_errors', List[str], None),
    ('msvc_compile_flags', List[str], None),
    ('msvc_resource_files', List[str], None)
  ]

  def __init__(self, **kwargs):
    if kwargs.get('msvc_nodefaultlib') == True:
      kwargs['msvc_nodefaultlib'] = ['']
    super().__init__(**kwargs)
"""

class MsvcCompiler(base.Compiler):

  id = 'msvc'
  name = 'Microsoft Visual C++'

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
  optimize_none_flag = '/Od'
  optimize_speed_flag = '/O2'
  optimize_size_flag = ['/O1', '/Os']
  enable_exceptions = '/EHsc'
  disable_exceptions = []
  enable_rtti = '/GR'
  disable_rtti = '/GR-'
  force_include = ['/FI', '%ARG%']
  save_temps = ['/P', '/Fi$out.i']  # TODO: Prevents the compilation step. :(

  linker_c = ['link', '/nologo']
  linker_cpp = linker_c
  linker_out = '/OUT:${out,product}'
  linker_shared = '/DLL'
  linker_exe = []
  linker_lib = '%ARG%.lib'
  linker_libpath = '/LIBPATH:%ARG%'
  linker_runtime = {}  # Required flags will be added in build_compile_flags()

  archiver = ['lib', '/nologo']
  archiver_out = '/OUT:${out,product}'

  executable_suffix = '.exe'
  library_prefix = ''
  library_shared_suffix = '.dll'
  library_static_suffix = '.lib'

  def __init__(self, toolkit):
    super().__init__(
      version = toolkit.cl_version,
      arch = toolkit.cl_info.target,
      compiler_env = toolkit.environ,
      linker_env = toolkit.environ,
      archiver_env = toolkit.environ,
      deps_prefix = toolkit.deps_prefix
    )
    self.toolkit = toolkit

  def init(self, context):
    props = context.target_properties
    props.add('cxx.msvcDisableWarnings', craftr.StringList)
    props.add('cxx.msvcWaringsAsErrors', craftr.StringList)
    props.add('cxx.msvcCompilerFlags', craftr.StringList)
    props.add('cxx.msvcLinkerFlags', craftr.StringList)
    props.add('cxx.msvcNoDefaultLib', craftr.StringList)
    props.add('cxx.msvcResourceFiles', craftr.PathList)
    props.add('cxx.msvcConformance', craftr.StringList, options={'inherit': True})

  # @override
  def translate_target(self, target, data):
    src_dir = target.directory
    obj_dir = path.join(target.output_directory, 'obj')
    if data.msvcResourceFiles:
      outfiles = craftr.relocate_files(src_dir, data.msvcResourceFiles, obj_dir, '.res')
      command = ['rc', '/r', '/nologo', '/fo', '$out', '$in']
      action = target.add_action(
        'cxx.msvcRc',
        commands = [command],
        environ = self.compiler_env
      )
      buildset = action.add_buildset()
      buildset.files.add(data.msvcResourceFiles, ['in'])
      buildset.files.add(outfiles, ['out', 'obj'])   # Include in the link step

  # @override
  def get_compile_command(self, target, data, lang):
    if data.separateDebugInformation is None:
      data.separateDebugInformation = False

    command = super().get_compile_command(target, data, lang)

    if BUILD.debug:
      command += ['/Od', '/RTC1', '/FC']
      if not self.version or self.version >= '18':
        # Enable parallel writes to .pdb files.
        command += ['/FS']
      if data.separateDebugInformation:
        command += ['/Zi', '/Fd${out,pdb}']  # TODO: no .pdb files generated.?
      else:
        command += ['/Z7']
    command += ['/wd' + str(x) for x in unique(data.msvcDisableWarnings)]

    if not data.runtimeLibrary:
      data.runtimeLibrary = 'dynamic'
    if data.runtimeLibrary == 'static':
      command += ['/MTd' if BUILD.debug else '/MT']
    elif data.runtimeLibrary == 'dynamic' or data.runtimeLibrary is None:
      command += ['/MDd' if BUILD.debug else '/MD']
    else:
      error('invalid cxx.runtimeLibrary: {!r}'.format(data.runtimeLibrary))

    command += ['/we' + str(x) for x in unique(data.msvcWaringsAsErrors)]
    command += data.msvcCompilerFlags

    for conf in data.msvcConformance:
      arg = '/Zc:' + conf
      command.append(arg)

    if self.deps_prefix:
      command += ['/showIncludes']
    return command

  # @override
  def add_objects_for_source(self, target, data, lang, src, buildset, objdir):
    rel = path.rel(src, target.directory)
    obj = path.setsuffix(path.join(objdir, rel), '.obj')
    buildset.files.add(obj, ['out', 'obj'])

    if BUILD.debug and data.separateDebugInformation:
      pdb = path.setsuffix(obj, '.pdb')
      buildset.files.add(pdb, ['out', 'pdb', 'optional'])

  # @override
  def get_link_command(self, target, data, lang):
    command = super().get_link_command(target, data, lang)
    command += [
      ('/NODEFAULTLIB:' + x) if x else '/NODEFAULTLIB'
      for x in unique(data.msvcNoDefaultLib)
    ]
    if base.is_sharedlib(data):
      command += ['/IMPLIB:${out,implib}']  # set from add_link_outputs()
    if BUILD.debug and base.is_sharedlib(data):
      command += ['/DEBUG']
    return command

  # @override
  def add_link_outputs(self, target, data, lang, buildset):
    if base.is_sharedlib(data):
      implib = path.setsuffix(data.productFilename, '.lib')
      buildset.files.add(implib, ['out', 'implib'])


def get_compiler(fragment):
  if fragment:
    log.warn('craftr/lang/cxx/msvc: Fragment not supported. (fragment = {!r})'
      .format(fragment))
  return MsvcCompiler(msvc.MsvcToolkit.from_config())

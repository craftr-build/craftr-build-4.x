
import craftr
import logging as log
import nr.path as path
import nr.stream
from typing import Union, List

base = load('./base.py')
msvc = load('tools.msvc')
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

  def on_target_created(self, build):
    if build.options.msvc_resource_files and build.localize_srcs:
      build.options.msvc_resource_files = [craftr.localpath(x) for x in build.options.msvc_resource_files]

  def before_link(self, build):
    result = []
    options = build.options
    obj_dir = path.join(build.namespace.build_directory, 'obj', build.target.name)
    if options.msvc_resource_files:
      outfiles = craftr.relocate_files(options.msvc_resource_files, obj_dir, '.res', parent=build.namespace.directory)
      command = ['rc', '/r', '/nologo', '/fo', '$out', '$in']
      result.append(build.target.add_action(
        name = 'rc',
        commands = [command],
        environ = self.toolkit.environ,
        input_files = options.msvc_resource_files,
        output_files = outfiles,
        foreach=True
      ))
      build.additional_link_files.extend(outfiles)
    return result

  def build_compile_flags(self, lang, target, data):
    if data.separateDebugInformation is None:
      data.separateDebugInformation = False

    command = super().build_compile_flags(lang, target, data)
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

    if self.deps_prefix:
      command += ['/showIncludes']
    return command

  def update_compile_buildset(self, build, target, data):
    # TODO: Select the obj filename in the build directory.
    src = next(build.files.tagged('src'))
    obj = path.setsuffix(src, '.obj')
    build.files.add(obj, ['out', 'obj'])
    if BUILD.debug and data.separateDebugInformation:
      pdb = path.setsuffix(src, '.pdb')
      build.files.add(pdb, ['out', 'pdb', 'optional'])

  def build_link_flags(self, lang, target, data):
    command = super().build_link_flags(lang, target, data)
    command += [
      ('/NODEFAULTLIB:' + x) if x else '/NODEFAULTLIB'
      for x in unique(data.msvcNoDefaultLib)
    ]
    if base.is_sharedlib(data):
      command += ['/IMPLIB:${out,implib}']  # set from set_target_outputs()
    if BUILD.debug and base.is_sharedlib(data):
      command += ['/DEBUG']
    return command

  def update_link_buildset(self, build, target, data):
    out = next(build.files.tagged('out,product'))
    if base.is_sharedlib(data):
      implib = path.setsuffix('.lib')
      build.files.add(implib, ['out', 'implib'])


def get_compiler(fragment):
  if fragment:
    log.warn('craftr/lang/cxx/msvc: Fragment not supported. (fragment = {!r})'
      .format(fragment))
  return MsvcCompiler(msvc.MsvcToolkit.from_config())

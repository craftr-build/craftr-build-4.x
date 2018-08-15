
import nr.types
import {options} from '../build.craftr'

from craftr.api import *
from craftr.core import build
from craftr.core.template import TemplateCompiler
from typing import List, Dict, Union, Callable
from nr.stream import stream

options('namingScheme', str, '')

if not options.namingScheme:
  if OS.id == 'win32':
    options.namingScheme = 'e=.exe,lp=,ls=.lib,ld=.dll'
  elif OS.id == 'darwin':
    options.namingScheme = 'e=,lp=lib,ls=.a,ld=.dylib'
  else:
    options.namingScheme = 'e=,lp=lib,ls=.a,ld=.so'

naming_scheme = {k.lower(): v for k, v in (
  x.partition('=')[::2] for x in options.namingScheme.split(','))}


def short_path(x):
  y = path.rel(x, par=True)
  return x if len(x) < len(y) else y


def is_sharedlib(data):
  return data.type == 'library' and data.preferredLinkage == 'shared'


def is_staticlib(data):
  return data.type == 'library' and data.preferredLinkage == 'static'


class Compiler(nr.types.Named):
  """
  Represents the flags necessary to support the compilation and linking with
  a compiler in Craftr. Flag-information that expects an argument may have a
  `%ARG%` string included which will then be substituted for the argument. If
  it is not present, the argument will be appended to the flags.
  """

  __annotations__ = [
    ('id', str),
    ('name', str),
    ('version', str),
    ('arch', str),

    ('executable_suffix', str),
    ('library_prefix', str),
    ('library_shared_suffix', str),
    ('library_static_suffix', str),

    ('compiler_c', List[str]),               # Arguments to invoke the C compiler.
    ('compiler_cpp', List[str]),             # Arguments to invoke the C++ compiler.
    ('compiler_env', Dict[str, str]),        # Environment variables for the compiler.
    ('compiler_out', List[str]),             # Specify the compiler object output file.

    ('c_std', List[str]),
    ('c_stdlib', List[str], []),
    ('cpp_std', List[str]),
    ('cpp_stdlib', List[str], []),
    ('pic_flag', List[str]),                 # Flag(s) to enable position independent code.
    ('debug_flag', List[str]),               # Flag(s) to enable debug symbols.
    ('define_flag', str),                    # Flag to define a preprocessor macro.
    ('include_flag', str),                   # Flag to specify include directories.
    ('expand_flag', List[str]),              # Flag(s) to request macro-expanded source.
    ('warnings_flag', List[str]),            # Flag(s) to enable all warnings.
    ('warnings_as_errors_flag', List[str]),  # Flag(s) to turn warnings into errors.
    ('optimize_none_flag', List[str]),
    ('optimize_speed_flag', List[str]),
    ('optimize_size_flag', List[str]),
    ('enable_exceptions', List[str]),
    ('disable_exceptions', List[str]),
    ('enable_rtti', List[str]),
    ('disable_rtti', List[str]),
    ('force_include', List[str]),
    ('save_temps', List[str]),               # Flags to save temporary files during the compilation step.
    ('depfile_args', List[str], []),         # Arguments to enable writing a depfile or producing output for deps_prefix.
    ('depfile_name', str, None),             # The deps filename. Usually, this would contain the variable $out.
    ('deps_prefix', str, None),              # The deps prefix (don't mix with depfile_name).

    # OpenMP settings.
    ('compiler_supports_openmp', bool, False),
    ('compiler_enable_openmp', List[str], None),
    ('linker_enable_openmp', List[str], None),

    ('linker_c', List[str]),                 # Arguments to invoke the linker for C programs.
    ('linker_cpp', List[str]),               # Arguments to invoke the linker for C++/C programs.
    ('linker_env', Dict[str, str]),          # Environment variables for the binary linker.
    ('linker_out', List[str]),               # Specify the linker output file.
    ('linker_shared', List[str]),            # Flag(s) to link a shared library.
    ('linker_exe', List[str]),               # Flag(s) to link an executable binary.
    ('linker_lib', List[str]),
    ('linker_libpath', List[str]),

    # A dictionary for flags {lang: {static: [], dynamic: []}}
    # Non-existing keys will have appropriate default values.
    ('linker_runtime', Dict[str, Dict[str, List[str]]], nr.types.Named.Initializer(dict)),

    # XXX support MSVC /WHOLEARCHIVE

    ('archiver', List[str]),                 # Arguments to invoke the archiver.
    ('archiver_env', List[str]),             # Environment variables for the archiver.
    ('archiver_out', List[str]),             # Flag(s) to specify the output file.
  ]

  executable_suffix = naming_scheme.get('e', '')
  library_prefix = naming_scheme.get('lp', '')
  library_shared_suffix = naming_scheme.get('ld', '')
  library_static_suffix = naming_scheme.get('ls', '')

  @property
  def is32bit(self):
    return self.arch == 'x86'

  @property
  def is64bit(self):
    return self.arch == 'x64'

  def __repr__(self):
    return '<{} name={!r} version={!r}>'.format(type(self).__name__, self.name, self.version)

  def info_string(self):
    return '{} ({}) {} for {}'.format(
      self.name,
      self.id,
      self.version,
      self.arch)

  def expand(self, args, value=None):
    if isinstance(args, str):
      args = [args]
    if value is not None:
      return [x.replace('%ARG%', value) for x in args]
    return list(args)

  # @override
  def init(self):
    """
    Called from CxxTargetHandler.init().
    """

  def translate_target(self, target, data):
    """
    Called to allow the compiler additional translation steps.
    """

  def get_compile_command(self, target, data, lang):
    """
    This method is called to generate a command to build a C or C++ source
    file into an object file. The command must use action variables to
    reference any files used by the command, eg. commonly `${in,src}` and
    `${out,obj}`.

    The default implementation of this method constructs a command based on
    the data members of the #Compiler subclass.
    """

    if data.type not in ('executable', 'library'):
      error('invalid cxx.type: {!r}'.format(data.type))

    defines = list(data.defines)
    if data.type == 'library' and data.preferredLinkage == 'shared':
      defines += list(data.definesForSharedBuild)
    elif data.type == 'library' and data.preferredLinkage == 'static':
      defines += list(data.definesForStaticBuild)

    includes = [short_path(x) for x in data.includes]
    flags = list(data.compilerFlags)
    forced_includes = list(data.prefixHeaders)

    if data.enableOpenmp:
      if not self.compiler_supports_openmp:
        print('[WARNING]: Compiler does not support OpenMP')
      else:
        flags += self.compiler_enable_openmp

    # TODO: Find exported information from dependencies.
    """
    for dep in build.target.deps(with_behaviour=CxxBuild).attr('impl'):
      includes.extend(dep.exported_includes)
      defines.extend(dep.exported_defines)
      forced_includes.extend(dep.exported_forced_includes)
      flags.extend(dep.exported_compiler_flags)
      if dep.type == 'library' and dep.preferred_linkage == 'shared':
        defines.extend(dep.exported_shared_defines)
      else:
        defines.extend(dep.exported_static_defines)
    for dep in build.target.deps(with_behaviour=CxxPrebuilt).attr('impl'):
      includes.extend(dep.includes)
      defines.extend(dep.defines)
      flags.extend(dep.compiler_flags)
      forced_includes.extend(dep.forced_includes)
    """

    command = self.expand(getattr(self, 'compiler_' + lang))
    command.append('${<src}')
    command.extend(self.expand(self.compiler_out, '${@obj}'))

    if data.saveTemps:
      command.extend(self.expand(self.save_temps))

    # c_std, cpp_std
    std_value = getattr(data, lang + 'Std')
    if std_value:
      command.extend(self.expand(getattr(self, lang + '_std'), std_value))
    # c_stdlib, cpp_stdlib
    stdlib_value = getattr(data, lang + 'Stdlib')
    if stdlib_value:
      command.extend(self.expand(getattr(self, lang + '_stdlib'), stdlib_value))

    for include in includes:
      command.extend(self.expand(self.include_flag, include))
    for define in defines:
      command.extend(self.expand(self.define_flag, define))
    command.extend(flags)
    if is_sharedlib(data):
      command += self.expand(self.pic_flag)

    if data.warningLevel == 'all':
      command.extend(self.expand(self.warnings_flag))
    if data.treatWarningsAsErrors:
      command.extend(self.expand(self.warnings_as_errors))
    command.extend(self.expand(self.enable_exceptions if data.enableExceptions else self.disable_exceptions))
    command.extend(self.expand(self.enable_rtti if data.enableRtti else self.disable_rtti))
    if not BUILD.debug and data.optimization:
      command += self.expand(getattr(self, 'optimize_' + data.optimization + '_flag'))
    if BUILD.debug:
      command += self.expand(self.debug_flag)
    if forced_includes:
      command += stream.concat(self.expand(self.force_include, x) for x in forced_includes)

    if self.depfile_args:
      command += self.expand(self.depfile_args)

    return command

  def create_compile_action(self, target, data, action_name, lang, srcs):
    command = self.get_compile_command(target, data, lang)
    op = operator(action_name, commands=[command], environ=self.compiler_env,
                  deps_prefix=self.deps_prefix)

    objdir = path.join(target.build_directory, 'obj')
    for src in srcs:
      bset = BuildSet({'src': src}, {})
      self.add_objects_for_source(target, data, lang, src, bset, objdir)
      obj_file = bset.outputs['obj'][0]
      if self.depfile_name:
        bset.depfile = TemplateCompiler().compile(self.depfile_name).render({}, {'obj': [obj_file]}, {})[0]
      op.add_build_set(bset)

    return op

  def add_objects_for_source(sefl, target, data, lang, src, buildset, objdir):
    """
    This method is called from #create_compile_action() in order to construct
    the object output filename for the specified C or C++ source file and add
    it to the *buildset*. Additional files may also be added, for example the
    MSVC compiler will add the PDB file.

    The object file must be tagged as `out` and `obj`. Additional output files
    should be tagged with at least `out` and maybe `optional`.
    """

    raise NotImplementedError

  def get_link_command(self, target, data, lang):
    """
    Similar to #get_compile_command(), this method is called to generate a
    command to link object files to an executable, shared library or static
    library.
    """

    is_archive = False
    is_shared = False

    if data.type == 'library':
      if data.preferredLinkage == 'shared':
        is_shared = True
      elif data.preferredLinkage == 'static':
        is_archive = True
      else:
        assert False, data.preferredLinkage
    elif data.type == 'executable':
      pass
    else:
      assert False, data.type

    if not data.runtimeLibrary:
      data.runtimeLibrary = 'static' if options.staticRuntime else 'dynamic'

    if is_archive:
      command = self.expand(self.archiver)
      command.extend(self.expand(self.archiver_out, '${@product}'))
    else:
      command = self.expand(self.linker_cpp if lang == 'cpp' else self.linker_c)
      command.extend(self.expand(self.linker_out, '${@product}'))
      command.extend(self.expand(self.linker_shared if is_shared else self.linker_exe))

    flags = list(data.linkerFlags)
    if data.enableOpenmp and self.compiler_supports_openmp:
      flags += self.linker_enable_openmp

    # TODO: Tell the compiler to link staticLibraries and dynamicLibraries
    #       statically/dynamically respectively?
    libs = data.systemLibraries + data.staticLibraries + data.dynamicLibraries

    # Inherit options from dependencies.
    """
    for dep_target in target.transitive_dependencies().attr('sources').concat():
      libs += dep.exported_syslibs
      if dep.type == 'library':
        additional_input_files.extend(dep.linkname_full or dep.outname_full)
        flags.extend(dep.linker_flags)
    for dep in build.target.deps(with_behaviour=CxxPrebuilt).attr('impl'):
      libs += dep.syslibs
      libpath += dep.libpath
      flags.extend(dep.linker_flags)
      if build.link_style == 'static' and dep.static_libs or not dep.shared_libs:
        additional_input_files.extend(dep.static_libs)
      elif build.link_style == 'shared' and dep.shared_libs or not dep.static_libs:
        additional_input_files.extend(dep.shared_libs)
    """

    if not is_staticlib(data):
      runtime = self.linker_runtime.get(lang, {})
      if data.runtimeLibrary == 'static':
        flags += self.expand(runtime.get('static', []))
      else:
        flags += self.expand(runtime.get('dynamic', []))

    flags += stream.concat([self.expand(self.linker_libpath, x) for x in stream.unique(data.libraryPaths)])
    if not is_staticlib(data):
      flags += stream.concat([self.expand(self.linker_lib, x) for x in stream.unique(libs)])

    return command + ['$<in'] + flags
    
  def get_link_commands(self, target, data, lang):
    command = self.get_link_command(target, data, lang)
    linker_cmd_len = len(self.linker_cpp if lang == 'cpp' else self.linker_c)
    command = build.Command(command, supports_response_file=True,
                            response_args_begin=linker_cmd_len)
    return [command]

  def create_link_action(self, target, data, action_name, lang, object_files):
    commands = self.get_link_commands(target, data, lang)
    input_files = list(object_files) + data.outLinkLibraries
    op = operator(action_name, commands=commands, environ=self.linker_env)
    bset = BuildSet({'in': input_files}, {'product': data.productFilename})
    self.add_link_outputs(target, data, lang, bset)
    op.add_build_set(bset)
    return op

  def add_link_outputs(self, target, data, lang, buildset):
    if is_staticlib(data):
      properties({'@+cxx.outLinkLibraries': [data.productFilename]}, target=target)

  def on_completion(self, target, data):
    pass

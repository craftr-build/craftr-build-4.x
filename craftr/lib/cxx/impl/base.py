
import craftr
import nr.named
import nr.stream
from typing import List, Dict, Union, Callable

concat = nr.stream.stream.concat
unique = nr.stream.stream.unique


def is_sharedlib(data):
  return data.type == 'library' and data.preferredLinkage == 'shared'


def is_staticlib(data):
  return data.type == 'library' and data.preferredLinkage == 'shared'


class Compiler(nr.named.named):
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
    ('linker_runtime', Dict[str, Dict[str, List[str]]], nr.named.initializer(dict)),

    # XXX support MSVC /WHOLEARCHIVE

    ('archiver', List[str]),                 # Arguments to invoke the archiver.
    ('archiver_env', List[str]),             # Environment variables for the archiver.
    ('archiver_out', List[str]),             # Flag(s) to specify the output file.
  ]

  @property
  def is32bit(self):
    return self.arch == 'x86'

  @property
  def is64bit(self):
    return self.arch == 'x64'

  def __repr__(self):
    return '<{} name={!r} version={!r}>'.format(type(self).__name__, self.name, self.version)

  def expand(self, args, value=None):
    if isinstance(args, str):
      args = [args]
    if value is not None:
      return [x.replace('%ARG%', value) for x in args]
    return list(args)

  def init(self, context):
    pass

  def before_translate(self, build):
    pass

  def before_compile(self, build):
    """
    Calld before #build_compile_flags(). Allows you to create additional
    build actions. Return a list of build actions that will be added as
    deps to the compile step.
    """

    return None

  def before_link(self, build):
    """
    Called before #build_link_flags(). Allows you to create additional
    build actions. Return a list of build actions that will be added as
    deps to the link step.
    """

    return None

  def build_compile_flags(self, lang, target, data):
    """
    Build the compiler flags. Does not include the #compiler_out argument,
    yet. Use the #build_compile_out_flags() method for that.
    """

    if not data.preferredLinkage:
      data.preferredLinkage = 'static'
    if data.preferredLinkage not in ('static', 'shared'):
      error('invalid cxx.preferredLinkage: {!r}'.format(data.preferredLinkage))
    if data.type not in ('executable', 'library'):
      error('invalid cxx.type: {!r}'.format(data.type))

    defines = list(data.defines)
    if data.type == 'library' and data.preferredLinkage == 'shared':
      defines += list(data.definesForSharedBuild)
    elif data.type == 'library' and data.preferredLinkage == 'static':
      defines += list(data.definesForStaticBuild)

    includes = list(data.includes)
    flags = list(data.compilerFlags)
    forced_includes = list(data.prefixHeaders)

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
    command.append('${in&src}')
    command.extend(self.expand(self.compiler_out, '${out&obj}'))

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
    if not BUILD.debug:
      command += self.expand(getattr(self, 'optimize_' + data.optimization + '_flag'))
    if forced_includes:
      command += concat(self.expand(self.force_include, x) for x in forced_includes)

    if self.depfile_args:
      command += self.expand(self.depfile_args)

    return command

  def update_compile_buildset(self, build, target, data):
    raise NotImplementedError

  def build_link_flags(self, lang, target, data):
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

    if is_archive:
      command = self.expand(self.archiver)
      command.extend(self.expand(self.archiver_out, '${out&product}'))
    else:
      command = self.expand(self.linker_cpp if lang == 'cpp' else self.linker_c)
      command.extend(self.expand(self.linker_out, '${out&product}'))
      command.extend(self.expand(self.linker_shared if is_shared else self.linker_exe))

    flags = []
    libs = list(data.staticLibraries) + list(data.dynamicLibraries) # TODO: Handle these differently?
    libpath = list(data.libraryPaths)

    # TODO: Inherit options from dependencies?
    """
    for dep in build.target.deps(with_behaviour=CxxBuild).attr('impl'):
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

    flags += concat([self.expand(self.linker_libpath, x) for x in unique(libpath)])
    if not is_staticlib(data):
      flags += concat([self.expand(self.linker_lib, x) for x in unique(libs)])
    return command + ['$in'] + flags #+ additional_input_files

  def update_link_buildset(self, build, target, data):
    raise NotImplementedError



from typing import List, Dict, Union, Callable, Type
import functools
import logging as log
import nodepy
import re
import sys

import craftr from 'craftr'
import utils, {stream.concat as concat, stream.unique as unique} from 'craftr/utils'
import path from 'craftr/utils/path'
import macro from 'craftr/utils/macro'
import path from 'craftr/utils/path'


def infer_linkage(target):
  choices = set()
  for build in target.dependents(with_behaviour=CxxBuild).attr('impl'):
    choices.add(build.link_style)
  if len(choices) > 1:
    log.warn('Target "{}" has preferred_linkage=any, but dependents '
      'specify conflicting link_styles {}. Falling back to static.'
      .format(target.long_name, choices))
    preferred_linkage = 'static'
  elif len(choices) == 1:
    preferred_linkage = choices.pop()
  else:
    preferred_linkage = craftr.options.get('cxx.preferred_linkage', 'static')
    if preferred_linkage not in ('static', 'shared'):
      raise RuntimeError('invalid cxx.preferred_linkage option: {!r}'
        .format(preferred_linkage))
  return preferred_linkage


def infer_bool(target, attr, default):
  for build in target.dependents(with_behaviour=CxxBuild).attr('impl'):
    if getattr(build, attr):
      return True
  else:
    return default


def infer_optimize(target):
  for build in target.dependents(with_behaviour=CxxBuild).attr('impl'):
    if build.optimize:
      return build.optimize
  return craftr.options.get('cxx.optimize', 'speed')


class CxxBuild(craftr.Behaviour):

  def init(self,
        type: str,
        srcs: List[str] = None,
        c_std = None,
        cpp_std = None,
        debug: bool = None,
        warnings: bool = True,
        warnings_as_errors: bool = False,
        optimize: str = None,
        exceptions: bool = None,
        static_defines: List[str] = None,
        exported_static_defines: List[str] = None,
        shared_defines: List[str] = None,
        exported_shared_defines: List[str] = None,
        includes: List[str] = None,
        exported_includes: List[str] = None,
        defines: List[str] = None,
        exported_defines: List[str] = None,
        forced_includes: List[str] = None,
        exported_forced_includes: List[str] = None,
        compiler_flags: List[str] = None,
        exported_compiler_flags: List[str] = None,
        linker_flags: List[str] = None,
        exported_linker_flags: List[str] = None,
        syslibs: List[str] = None,
        exported_syslibs: List[str] = None,
        link_style: str = None,
        preferred_linkage: str = 'any',
        static_runtime: bool = None,
        outname: str = '$(lib)$(name)$(ext)',
        outdir: str = NotImplemented,
        unity_build: bool = None,
        compiler: 'Compiler' = None,
        options: Dict = None,
        localize_srcs: bool = True):
    assert compiler and isinstance(compiler, Compiler)
    if type not in ('library', 'binary'):
      raise ValueError('invalid type: {!r}'.format(type))
    if optimize not in (None, 'speed', 'size'):
      raise ValueError('invalid value for optimize: {!r}'.format(optimize))
    if not link_style:
      link_style = craftr.options.get('cxx.link_style', 'static')
    if link_style not in ('static', 'shared'):
      raise ValueError('invalid link_style: {!r}'.format(link_style))
    if preferred_linkage not in ('any', 'static', 'shared'):
      raise ValueError('invalid preferred_linkage: {!r}'.format(preferred_linkage))
    if isinstance(srcs, str):
      srcs = [srcs]
    if options is None:
      options = {}
    if isinstance(options, dict):
      options = compiler.options_class(**options)
    if not isinstance(options, compiler.options_class):
      raise TypeError('options must be None, dict or {}, got {} instead'
        .format(compilre.options_class.__name__, type(options).__name__))
    self.srcs = [craftr.localpath(x) for x in (srcs or [])] if localize_srcs else (srcs or [])
    if not self.srcs:
      raise ValueError('srcs must have minimum length 1')
    if outdir is NotImplemented:
      outdir = self.namespace.build_directory
    self.type = type
    self.debug = debug
    self.c_std = c_std
    self.cpp_std = cpp_std
    self.warnings = warnings
    self.warnings_as_errors = warnings_as_errors
    self.optimize = optimize
    self.exceptions = exceptions
    self.static_defines = static_defines or []
    self.exported_static_defines = exported_static_defines or []
    self.shared_defines = shared_defines or []
    self.exported_shared_defines = exported_shared_defines or []
    self.includes = [craftr.localpath(x) for x in (includes or [])]
    self.exported_includes = [craftr.localpath(x) for x in (exported_includes or [])]
    self.defines = defines or []
    self.exported_defines = exported_defines or []
    self.forced_includes = forced_includes or []
    self.exported_forced_includes = exported_forced_includes or []
    self.compiler_flags = compiler_flags or []
    self.exported_compiler_flags = exported_compiler_flags or []
    self.linker_flags = linker_flags or []
    self.exported_linker_flags = exported_linker_flags or []
    self.syslibs = syslibs or []
    self.exported_syslibs = exported_syslibs or []
    self.link_style = link_style
    self.preferred_linkage = preferred_linkage
    self.static_runtime = static_runtime
    self.outname = outname
    self.outdir = outdir
    self.unity_build = unity_build
    self.compiler = compiler
    self.options = options
    self.additional_outputs = []
    self.additional_link_files = []
    self.localize_srcs = localize_srcs

    if self.is_foreach():
      if len(outname) != len(self.srcs):
        raise ValueError('if outname is a list, it must have the same length as srcs')
    elif not isinstance(self.outname, str):
      raise ValueError('outname must be a list or str')

    if self.unity_build is None:
      if self.is_foreach():
        self.unity_build = False
      else:
        unity_build = bool(craftr.options.get('cxx.unity_build', False))
    elif self.unity_build and self.is_foreach():
      raise ValueError('unity_build can not be combined with foreach build target')

    # Set after translate().
    self.outname_full = None
    # Required for MSVC because the file to link with is different
    # than the actual output DLL output file.
    self.linkname_full = None

    if self.options.__unknown_options__:
      log.warn('[{}]: Unknown compiler option(s): {}'.format(
        self.target.identifier(), ', '.join(self.options.__unknown_options__.keys())))

    compiler.on_target_created(self)

  def is_foreach(self):
    return isinstance(self.outname, list)

  def is_staticlib(self):
    return self.type == 'library' and self.preferred_linkage == 'static'

  def is_sharedlib(self):
    return self.type == 'library' and self.preferred_linkage == 'shared'

  def is_binary(self):
    return self.type == 'binary'

  def has_cpp_sources(self):
    for fname in self.srcs:
      if fname.endswith('.cpp') or fname.endswith('.cc'):
        return True
    return False

  def translate(self):
    self.compiler.before_translate(self)

    # Update the preferred linkage of this target.
    if self.preferred_linkage == 'any':
      self.preferred_linkage = infer_linkage(self.target)
    assert self.preferred_linkage in ('static', 'shared')

    # Inherit the debug option if it is not set.
    # XXX What do to on different values?
    if self.debug is None:
      self.debug = infer_bool(self.target, 'debug', not craftr.is_release)

    # Inherit static runtime property.
    if self.static_runtime is None:
      self.static_runtime = infer_bool(self.target, 'static_runtime',
          craftr.options.get('cxx.static_runtime', self.link_style == 'static'))

    # Inherit the optimize flag if it is not set.
    # XXX What do to on different values?
    if self.optimize is None:
      self.optimize = infer_optimize(self.target)
    if self.optimize not in ('speed', 'size'):
      raise RuntimeError('[{}] invalid optimize: {!r}'.format(
        self.target.long_name, self.optimize))

    if self.exceptions is None:
      self.exceptions = infer_bool(self.target, 'exceptions', True)

    # Separate C and C++ sources.
    c_srcs = []
    cpp_srcs = []
    unknown = []
    for src in self.srcs:
      if src.endswith('.cpp') or src.endswith('.cc'):
        cpp_srcs.append(src)
      elif src.endswith('.c'):
        c_srcs.append(src)
      else:
        unknown.append(src)
    if unknown:
      if c_srcs or not cpp_srcs:
        c_srcs.extend(unknown)
      else:
        cpp_srcs.extend(unknown)

    # Create the unity source file(s).
    if self.unity_build:
      for srcs, suffix in ((c_srcs, '.c'), (cpp_srcs, '.cpp')):
        if not srcs or len(srcs) == 1:
          continue
        unity_filename = path.join(self.namespace.build_directory, 'unity-source-' + self.target.name + suffix)
        path.makedirs(path.dir(unity_filename), exist_ok=True)
        with utils.SameContentKeepsTimestampFile(unity_filename, 'w') as fp:
          for filename in srcs:
            print('#include "{}"'.format(path.abs(filename)), file=fp)
        srcs[:] = [unity_filename]

    before_compile_actions = self.compiler.before_compile(self) or []

    ctx = macro.Context()
    self.compiler.init_macro_context(self, ctx)
    self.compiler.set_target_outputs(self, ctx)
    assert self.outname_full is not None, 'compiler.set_target_outputs() did not set outname_full'

    # Compile object files.
    obj_dir = path.join(self.namespace.build_directory, 'obj', self.target.name)
    obj_files = []
    obj_actions = []
    obj_suffix = macro.parse('$(obj)').eval(ctx, [])

    for lang, srcs in (('c', c_srcs), ('cpp', cpp_srcs)):
      if not srcs: continue
      # XXX Could result in clashing object file names!
      output_files = craftr.relocate_files(srcs, obj_dir, obj_suffix, parent=self.namespace.directory)
      command = self.compiler.build_compile_flags(self, lang)
      obj_actions.append(self.target.add_action(
        name = 'compile_' + lang,
        commands = [command],
        input = True,
        deps = before_compile_actions,
        environ = self.compiler.compiler_env,
        input_files = srcs,
        output_files = output_files,
        foreach = True,
        depfile = self.compiler.depfile_name,
        deps_prefix = self.compiler.deps_prefix
      ))
      obj_files.append(output_files)

    before_link_actions = self.compiler.before_link(self) or []

    additional_input_files = []
    command = self.compiler.build_link_flags(self, '$out', additional_input_files)

    outputs = list(self.outname_full)
    optional_outputs = []
    if self.linkname_full:
      optional_outputs.extend(self.linkname_full)

    self.target.add_action(
      name = 'link',
      commands = [command],
      deps = obj_actions + before_link_actions,
      output = True,
      environ = self.compiler.linker_env,
      input_files = list(concat(obj_files)) + additional_input_files + self.additional_link_files,
      output_files = outputs,
      optional_output_files = optional_outputs + self.additional_outputs,
    )


class CxxPrebuilt(craftr.Behaviour):

  def init(self,
               includes: List[str] = None,
               defines: List[str] = None,
               static_libs: List[str] = None,
               shared_libs: List[str] = None,
               compiler_flags: List[str] = None,
               linker_flags: List[str] = None,
               forced_includes: List[str] = None,
               syslibs: List[str] = None,
               libpath: List[str] = None,
               preferred_linkage: List[str] = 'any'):
    if preferred_linkage not in ('any', 'static', 'shared'):
      raise ValueError('invalid preferred_linkage: {!r}'.format(preferred_linkage))
    self.includes = [craftr.localpath(x) for x in (includes or [])]
    self.defines = defines or []
    self.static_libs = static_libs or []
    self.shared_libs = shared_libs or []
    self.compiler_flags = compiler_flags or []
    self.linker_flags = linker_flags or []
    self.forced_includes = forced_includes or []
    self.syslibs = syslibs or []
    self.libpath = libpath or []
    self.preferred_linkage = preferred_linkage

  def translate(self):
    pass


class CxxRun(craftr.Gentarget):

  def init(self, target_to_run, argv, **kwargs):
    super().init(commands=[], **kwargs)
    assert isinstance(target_to_run.impl, CxxBuild)
    self.target_to_run = target_to_run
    self.argv = argv

  def complete(self):
    self.target.explicit = True

  def translate(self):
    self.commands = []
    for filename in self.target_to_run.impl.outname_full:
      self.commands.append([filename] + list(self.argv))
    super().translate()


class CxxEmbed(craftr.Behaviour):
  """
  Embed one or more resource files into an executable or library.
  """

  def init(self, files, names=None, cfile=None, library_factory=None):
    if names is not None and len(names) != len(files):
      raise ValueError('len(names) must match len(files)')

    if names is None:
      names = []
      for fn in files:
        fn = path.rel(fn, self.namespace.directory)
        names.append(re.sub('[^\w\d_]+', '_', fn))

    if not cfile:
      cfile = path.join(self.namespace.build_directory, self.target.name + '_embedd.c')

    self.files = files
    self.names = names
    self.cfile = cfile
    self.build = (library_factory or library)(
      parent = self.target,
      name = 'lib',
      srcs = [self.cfile],
      deps = [self.target],
      localize_srcs = False
    )

  def translate(self):
    command = nodepy.runtime.exec_args + [str(require.resolve('craftr/tools/files2c').filename), '-o', self.cfile]
    for infile, cname in zip(self.files, self.names):
      command += ['{}:{}'.format(infile, cname)]
    self.target.add_action(
      name = 'files2c',
      commands = [command],
      input_files = self.files,
      output_files = [self.cfile]
    )
    self.build.translate()


class CompilerOptions(utils.named):
  """
  Base-class for the options supported by a specific compiler. Subclasses
  should provide annotations of the supported members. The constructor of this
  class accepts any keyword arguments, and will store all unknown options in
  the `__unknown_options__` dictionary.

  All options should have default values.
  """

  def __init__(self, **kwargs):
    self.__unknown_options__ = {}
    for key in tuple(kwargs.keys()):
      if key not in self.__annotations__:
        self.__unknown_options__[key] = kwargs.pop(key)
    super().__init__(**kwargs)

  def __repr__(self):
    return '<{} ({} unknown option(s))>'.format(type(self).__name__,
      len(self.__unknown_options__))


class Compiler(utils.named):
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
    ('options_class', Type[CompilerOptions]),

    ('compiler_c', List[str]),               # Arguments to invoke the C compiler.
    ('compiler_cpp', List[str]),             # Arguments to invoke the C++ compiler.
    ('compiler_env', Dict[str, str]),        # Environment variables for the compiler.
    ('compiler_out', List[str]),             # Specify the compiler object output file.

    ('c_std', List[str]),
    ('cpp_std', List[str]),
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
    ('force_include', List[str]),
    ('depfile_args', List[str], []),         # Arguments to enable writing a depfile or producing output for deps_prefix
    ('depfile_name', str, None),             # The deps filename. Usually, this would contain the variable $in.
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
    ('linker_runtime', Dict[str, Dict[str, List[str]]], utils.named_initializer(dict)),

    # XXX support MSVC /WHOLEARCHIVE

    ('archiver', List[str]),                 # Arguments to invoke the archiver.
    ('archiver_env', List[str]),             # Environment variables for the archiver.
    ('archiver_out', List[str]),             # Flag(s) to specify the output file.

    ('lib_macro', Union[str, Callable[[List[str]], str]], None),
    ('ext_lib_macro', Union[str, Callable[[List[str]], str]], None),
    ('ext_dll_macro', Union[str, Callable[[List[str]], str]], None),
    ('ext_exe_macro', Union[str, Callable[[List[str]], str]], None),
    ('obj_macro', Union[str, Callable[[List[str]], str]], None)
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

  def init_macro_context(self, build, ctx):
    """
    Initializes the context for macro evaluation in the #CxxBuild behaviour
    *build*. The following macros will be defined:

    * `$(lib <name>)` derived from #Compiler.lib_macro
    * `$(ext <name>)` and `$(ext <name>, <version>)` derived from
      #Compiler.ext_lib_macro, #Compiler.ext_dll_macro and
      #Compiler.ext_exe_macro
    * `$(obj <name>)` derived from #Compiler.obj_macro
    """

    if self.lib_macro and build.type == 'library':
      ctx.define('lib', self.lib_macro)

    if build.type == 'library':
      if build.preferred_linkage == 'static':
        ext_macro = self.ext_lib_macro
      elif build.preferred_linkage == 'shared':
        ext_macro = self.ext_dll_macro
      else:
        assert False, build.preferred_linkage

    elif build.type == 'binary':
      ext_macro = self.ext_exe_macro
    else:
      assert False, build.type
    if ext_macro:
      ctx.define('ext', ext_macro)
    if self.obj_macro:
      ctx.define('obj', self.obj_macro)
    ctx.define('name', build.target.name)

  def on_target_created(self, build):
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

  def build_compile_flags(self, build, language):
    """
    Build the compiler flags. Does not include the #compiler_out argument,
    yet. Use the #build_compile_out_flags() method for that.
    """

    assert isinstance(build, CxxBuild)
    assert build.preferred_linkage in ('static', 'shared')

    defines = list(build.defines) + list(build.exported_defines)
    if build.type == 'library' and build.preferred_linkage == 'shared':
      defines += list(build.shared_defines) + list(build.exported_shared_defines)
    else:
      defines += list(build.static_defines) + list(build.exported_static_defines)

    includes = list(build.includes) + list(build.exported_includes)
    flags = list(build.compiler_flags) + list(build.exported_compiler_flags)
    forced_includes = list(build.forced_includes) + list(build.exported_forced_includes)
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

    command = self.expand(getattr(self, 'compiler_' + language))
    command.append('$in')
    command.extend(self.expand(self.compiler_out, '$out'))

    std_value = getattr(build, language + '_std')
    if std_value:
      command.extend(self.expand(getattr(self, language + '_std'), std_value))
    for include in includes:
      command.extend(self.expand(self.include_flag, include))
    for define in defines:
      command.extend(self.expand(self.define_flag, define))
    command.extend(flags)
    if build.is_sharedlib():
      command += self.expand(self.pic_flag)

    if build.warnings:
      command.extend(self.expand(self.warnings_flag))
    if build.warnings_as_errors:
      command.extend(self.expand(self.warnings_as_errors))
    if build.exceptions:
      command.extend(self.expand(self.enable_exceptions))
    else:
      command.extend(self.expand(self.disable_exceptions))
    if not build.debug:
      command += self.expand(getattr(self, 'optimize_' + build.optimize + '_flag'))
    if forced_includes:
      command += concat(self.expand(self.force_include, x) for x in forced_includes)

    return command

  def build_link_flags(self, build, outfile, additional_input_files):
    assert isinstance(additional_input_files, list)
    is_archive = False
    is_shared = False

    if build.type == 'library':
      if build.preferred_linkage == 'shared':
        is_shared = True
      elif build.preferred_linkage == 'static':
        is_archive = True
      else:
        assert False, build.preferred_linkage
    elif build.type == 'binary':
      pass
    else:
      assert False, build.type

    if is_archive:
      command = self.expand(self.archiver)
      command.extend(self.expand(self.archiver_out, outfile))
    else:
      command = self.expand(self.linker_cpp if build.has_cpp_sources() else self.linker_c)
      command.extend(self.expand(self.linker_out, outfile))
      command.extend(self.expand(self.linker_shared if is_shared else self.linker_exe))

    flags = []
    libs = list(build.syslibs)
    libpath = list()
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

    if not build.is_staticlib():
      lang = 'cpp' if build.has_cpp_sources() else 'c'
      runtime = self.linker_runtime.get(lang, {})
      if build.static_runtime:
        flags += self.expand(runtime.get('static', []))
      else:
        flags += self.expand(runtime.get('dynamic', []))

    flags += concat([self.expand(self.linker_libpath, x) for x in unique(libpath)])
    if not build.is_staticlib():
      flags += concat([self.expand(self.linker_lib, x) for x in unique(libs)])
    return command + ['$in'] + flags #+ additional_input_files

  def set_target_outputs(self, build, ctx):
    assert isinstance(build, CxxBuild)
    outs = build.outname if build.is_foreach() else [build.outname]
    build.outname_full = [macro.parse(x).eval(ctx, []) for x in outs]
    if build.outdir:
      build.outname_full = [path.join(build.outdir, x) for x in build.outname_full]


def extmacro(without_version, with_version):
  """
  Returns a function that should be used for the #Compiler.ext_lib_macro,
  #Compiler.ext_dll_macro and #Compiler.ext_exe_macro members because the
  `$(ext)` macro should also support a *version* argument.

  Note that you should wrap the result in `staticmethod()` if you assign it
  to a member on class-level.
  """

  without_version = macro.parse(without_version)
  with_version = macro.parse(with_version)

  @macro.function
  def compiled_extmacro(ctx, args):
    if args and args[0]:
      return with_version.eval(ctx, args)
    else:
      return without_version.eval(ctx, args)

  return compiled_extmacro


def _load_compiler():
  name = craftr.options.get('cxx.compiler', None)
  if name is None:
    if sys.platform.startswith('win32'):
      name = 'msvc'
    elif sys.platform.startswith('darwin'):
      name = 'llvm'
    else:
      name = 'gcc'

  name, fragment = name.partition(':')[::2]
  module = require.try_('./' + name, name)
  return module.get_compiler(fragment)


compiler = _load_compiler()
build = craftr.Factory(CxxBuild, compiler=compiler)
library = functools.partial(build, type='library')
binary = functools.partial(build, type='binary')
prebuilt = craftr.Factory(CxxPrebuilt)
embed = craftr.Factory(CxxEmbed)


def run(target, *argv, name=None, **kwargs):
  target = craftr.resolve_target(target)
  if not name:
    name = target.name + '_run'
  kwargs.setdefault('explicit', True)
  kwargs.setdefault('console', True)
  return craftr.Factory(CxxRun)(
    name = name,
    deps = [target],
    target_to_run = target,
    argv = argv,
    **kwargs
  )


print('Selected compiler: {} ({}) {} for {}'.format(
  compiler.name, compiler.id, compiler.version, compiler.arch))

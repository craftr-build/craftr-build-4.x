"""
Base classes for implementing compilers.
"""

__all__ = [
  'infer_linkage',
  'infer_debug',
  'build',
  'prebuilt',
  'run',
  'embed',
  'CompilerOptions',
  'Compiler',
  'extmacro'
]

from typing import List, Dict, Union, Callable, Type
import nodepy
import logging as log
import re
import craftr, {options} from 'craftr'
import it from 'craftr/utils/it'
import macro from 'craftr/utils/macro'
import path from 'craftr/utils/path'
import types from 'craftr/utils/types'


def infer_linkage(target):
  choices = set()
  for trait in target.dependents_traits().of_type(build):
    choices.add(trait.link_style)
  if len(choices) > 1:
    log.warn('Target "{}" has preferred_linkage=any, but dependents '
      'specify conflicting link_styles {}. Falling back to static.'
      .format(target.long_name, choices))
    preferred_linkage = 'static'
  elif len(choices) == 1:
    preferred_linkage = choices.pop()
  else:
    preferred_linkage = options.get('cxx.preferred_linkage', 'static')
    if preferred_linkage not in ('static', 'shared'):
      raise RuntimeError('invalid cxx.preferred_linkage option: {!r}'
        .format(preferred_linkage))
  return preferred_linkage


def infer_debug(target):
  for trait in target.dependents_traits().of_type(build):
    if trait.debug:
      return True
  else:
    return not craftr.is_release


@craftr.TargetFactory
class build(craftr.TargetTrait):

  def __init__(self,
               type: str,
               srcs: List[str] = None,
               c_std = None,
               cpp_std = None,
               debug: bool = None,
               warnings: bool = True,
               warnings_as_errors: bool = False,
               optimize: str = None,
               static_defines: List[str] = None,
               exported_static_defines: List[str] = None,
               shared_defines: List[str] = None,
               exported_shared_defines: List[str] = None,
               includes: List[str] = None,
               exported_includes: List[str] = None,
               defines: List[str] = None,
               exported_defines: List[str] = None,
               compiler_flags: List[str] = None,
               exported_compiler_flags: List[str] = None,
               linker_flags: List[str] = None,
               exported_linker_flags: List[str] = None,
               syslibs: List[str] = None,
               exported_syslibs: List[str] = None,
               link_style: str = None,
               preferred_linkage: str = 'any',
               outname: str = '$(lib)$(name)$(ext)',
               unity_build: bool = None,
               compiler: 'Compiler' = None,
               options: Dict = None,
               localize_srcs: bool = True):
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
    self.type = type
    self.debug = debug
    self.c_std = c_std
    self.cpp_std = cpp_std
    self.warnings = warnings
    self.warnings_as_errors = warnings_as_errors
    self.optimize = optimize
    self.static_defines = static_defines or []
    self.exported_static_defines = exported_static_defines or []
    self.shared_defines = shared_defines or []
    self.exported_shared_defines = exported_shared_defines or []
    self.includes = [craftr.localpath(x) for x in (includes or [])]
    self.exported_includes = [craftr.localpath(x) for x in (exported_includes or [])]
    self.defines = defines or []
    self.exported_defines = exported_defines or []
    self.compiler_flags = compiler_flags or []
    self.exported_compiler_flags = exported_compiler_flags or []
    self.linker_flags = linker_flags or []
    self.exported_linker_flags = exported_linker_flags or []
    self.syslibs = syslibs or []
    self.exported_syslibs = exported_syslibs or []
    self.link_style = link_style
    self.preferred_linkage = preferred_linkage
    self.outname = outname
    self.unity_build = unity_build
    self.compiler = compiler
    self.options = options
    self.compile_step_deps = []

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

  def mounted(self, target):
    super().mounted(target)
    if self.options.__unknown_options__:
      log.warn('[{}]: Unknown compiler option(s): {}'.format(
        target.long_name, ', '.join(self.options.__unknown_options__.keys())))

  def translate(self):
    # Update the preferred linkage of this target.
    if self.preferred_linkage == 'any':
      self.preferred_linkage = infer_linkage(self.target)
    assert self.preferred_linkage in ('static', 'shared')

    # Inherit the debug option if it is not set.
    # XXX What do to on different values?
    if self.debug is None:
      self.debug = infer_debug(self.target)

    # Inherit the optimize flag if it is not set.
    # XXX What do to on different values?
    if self.optimize is None:
      for trait in self.target.dependents_traits().of_type(build):
        if trait.optimize:
          self.optimize = trait.optimize
          break
      else:
        self.optimize = options.get('cxx.optimize', 'speed')
      if self.optimize not in ('speed', 'size'):
        raise RuntimeError('[{}] invalid optimize: {!r}'.format(
          self.target.long_name, self.optimize))

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
        unity_filename = path.join(self.target.cell.build_directory, 'unity-source-' + self.target.name + suffix)
        path.makedirs(path.dir(unity_filename), exist_ok=True)
        with open(unity_filename, 'w') as fp:
          for filename in srcs:
            print('#include "{}"'.format(path.abs(filename)), file=fp)
        srcs[:] = [unity_filename]

    ctx = macro.Context()
    self.compiler.init_macro_context(self, ctx)
    self.compiler.set_target_outputs(self, ctx)
    assert self.outname_full is not None, 'compiler.set_target_outputs() did not set outname_full'

    # Compile object files.
    obj_dir = path.join(self.target.cell.build_directory, 'obj', self.target.name)
    obj_files = []
    obj_actions = []
    obj_suffix = macro.parse('$(obj)').eval(ctx, [])

    for lang, srcs in (('c', c_srcs), ('cpp', cpp_srcs)):
      if not srcs: continue
      # XXX Could result in clashing object file names!
      objfiles = [
        path.join(obj_dir, path.base(path.rmvsuffix(x)) + obj_suffix)
        for x in srcs
      ]
      command = self.compiler.build_compile_flags(self, lang)
      obj_actions.append(craftr.BuildAction(
        name = 'compile_' + lang,
        commands = [command],
        deps = self.compile_step_deps + [...],
        environ = self.compiler.compiler_env,
        input_files = srcs,
        output_files = objfiles,
        foreach = True
      ))
      self.target.add_action(obj_actions[-1])
      obj_files.extend(objfiles)

    if obj_files:
      additional_input_files = []
      command = self.compiler.build_link_flags(self, '$out', additional_input_files)
      outputs = list(self.outname_full)
      if self.linkname_full:
        outputs.extend(self.linkname_full)
      self.target.add_action(craftr.BuildAction(
        commands = [command],
        deps = obj_actions,
        environ = self.compiler.linker_env,
        input_files = obj_files + additional_input_files,
        output_files = outputs
      ))


@craftr.TargetFactory
class prebuilt(craftr.TargetTrait):

  def __init__(self,
               includes: List[str] = None,
               defines: List[str] = None,
               static_libs: List[str] = None,
               shared_libs: List[str] = None,
               compiler_flags: List[str] = None,
               linker_flags: List[str] = None,
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
    self.syslibs = syslibs or []
    self.libpath = libpath or []
    self.preferred_linkage = preferred_linkage

  def translate(self):
    pass


@craftr.TargetFactory
class run(craftr.gentarget.cls):

  def __init__(self, target_to_run, argv, **kwargs):
    super().__init__(commands=[], **kwargs)
    assert isinstance(target_to_run.trait, build)
    self.target_to_run = target_to_run
    self.argv = argv

  def complete(self):
    self.target.explicit = True

  def translate(self):
    assert self.target_to_run.is_translated, self.target_to_run
    self.commands = []
    for filename in self.target_to_run.trait.outname_full:
      self.commands.append([filename] + list(self.argv))
    super().translate()


@craftr.TargetFactory
class embed(craftr.TargetTrait):
  """
  Embed one or more resource files into an executable or library.
  """

  def __init__(self, files, names=None, cfile=None, compiler=None):
    if names is not None and len(names) != len(files):
      raise ValueError('len(names) must match len(files)')
    self.files = files
    self.names = names
    self.cfile = cfile
    self.compiler = compiler
    self.build_trait = None

  def subtraits(self):
    if self.build_trait:
      yield self.build_trait

  def complete(self):
    if self.names is None:
      self.names = []
      for fn in self.files:
        fn = path.rel(fn, target.cell.build_directory)
        self.names.append(re.sub('[^\w\d_]+', '_', fn))
    if not self.cfile:
      self.cfile = path.join(target.cell.build_directory, self.target.name + '_embedd.c')
    self.build_trait = build(
      self.target,
      srcs = [self.cfile],
      type = 'library',
      compiler = self.compiler,
      localize_srcs = False
    )
    self.target.add_trait(self.build_trait)

  def translate(self):
    command = nodepy.runtime.exec_args + [str(require.resolve('./tools/files2c').filename), '-o', self.cfile]
    for infile, cname in zip(self.files, self.names):
      command += ['{}:{}'.format(infile, cname)]
    gen = craftr.BuildAction(
      name = 'files2c',
      commands = [command],
      input_files = self.files,
      output_files = [self.cfile]
    )
    self.target.add_action(gen)
    self.build_trait.compile_step_deps.append(gen)
    self.build_trait.translate()


class CompilerOptions(types.NamedObject):
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


class Compiler(types.NamedObject):
  """
  Represents the flags necessary to support the compilation and linking with
  a compiler in Craftr. Flag-information that expects an argument may have a
  `%ARG%` string included which will then be substituted for the argument. If
  it is not present, the argument will be appended to the flags.
  """

  __annotations__ = [
    ('name', str),
    ('version', str),
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

    ('linker_c', List[str]),                 # Arguments to invoke the linker for C programs.
    ('linker_cpp', List[str]),               # Arguments to invoke the linker for C++/C programs.
    ('linker_env', Dict[str, str]),          # Environment variables for the binary linker.
    ('linker_out', List[str]),               # Specify the linker output file.
    ('linker_shared', List[str]),            # Flag(s) to link a shared library.
    ('linker_exe', List[str]),               # Flag(s) to link an executable binary.
    ('linker_lib', List[str]),
    ('linker_libpath', List[str]),
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

  def __repr__(self):
    return '<{} name={!r} version={!r}>'.format(type(self).__name__, self.name, self.version)

  def expand(self, args, value=None):
    if isinstance(args, str):
      args = [args]
    if value is not None:
      return [x.replace('%ARG%', value) for x in args]
    return list(args)

  def init_macro_context(self, trait, ctx):
    """
    Initializes the context for macro evaluation in the #build trait *trait*.
    The following macros will be defined:

    * `$(lib <name>)` derived from #Compiler.lib_macro
    * `$(ext <name>)` and `$(ext <name>, <version>)` derived from
      #Compiler.ext_lib_macro, #Compiler.ext_dll_macro and
      #Compiler.ext_exe_macro
    * `$(obj <name>)` derived from #Compiler.obj_macro
    """

    if self.lib_macro and trait.type == 'library':
      ctx.define('lib', self.lib_macro)

    if trait.type == 'library':
      if trait.preferred_linkage == 'static':
        ext_macro = self.ext_lib_macro
      elif trait.preferred_linkage == 'shared':
        ext_macro = self.ext_dll_macro
      else:
        assert False, trait.preferred_linkage

    elif trait.type == 'binary':
      ext_macro = self.ext_exe_macro
    else:
      assert False, trait.type
    if ext_macro:
      ctx.define('ext', ext_macro)
    if self.obj_macro:
      ctx.define('obj', self.obj_macro)
    ctx.define('name', trait.target.name)

  def build_compile_flags(self, trait, language):
    """
    Build the compiler flags. Does not include the #compiler_out argument,
    yet. Use the #build_compile_out_flags() method for that.
    """

    assert isinstance(trait, build)
    assert trait.preferred_linkage in ('static', 'shared')

    defines = list(trait.defines) + list(trait.exported_defines)
    if trait.type == 'library' and trait.preferred_linkage == 'shared':
      defines += list(trait.shared_defines) + list(trait.exported_shared_defines)
    else:
      defines += list(trait.static_defines) + list(trait.exported_static_defines)

    includes = list(trait.includes) + list(trait.exported_includes)
    flags = list(trait.compiler_flags) + list(trait.exported_compiler_flags)
    for dep in trait.target.dep_traits():
      if isinstance(dep, build):
        includes.extend(dep.exported_includes)
        defines.extend(dep.exported_defines)
        flags.extend(dep.exported_compiler_flags)
        if dep.type == 'library' and dep.preferred_linkage == 'shared':
          defines.extend(dep.exported_shared_defines)
        else:
          defines.extend(dep.exported_static_defines)
      elif isinstance(dep, prebuilt):
        includes.extend(dep.includes)
        defines.extend(dep.defines)
        flags.extend(dep.compiler_flags)

    command = self.expand(getattr(self, 'compiler_' + language))
    command.append('$in')
    command.extend(self.expand(self.compiler_out, '$out'))

    std_value = getattr(trait, language + '_std')
    if std_value:
      command.extend(self.expand(getattr(self, language + '_std'), std_value))
    for include in includes:
      command.extend(self.expand(self.include_flag, include))
    for define in defines:
      command.extend(self.expand(self.define_flag, define))
    command.extend(flags)
    if trait.is_sharedlib():
      command += self.expand(self.pic_flag)

    if trait.warnings:
      command.extend(self.expand(self.warnings_flag))
    if trait.warnings_as_errors:
      command.extend(self.expand(self.warnings_as_errors))
    if not trait.debug:
      command += self.expand(getattr(self, 'optimize_' + trait.optimize + '_flag'))

    return command

  def build_link_flags(self, trait, outfile, additional_input_files):
    assert isinstance(additional_input_files, list)
    is_archive = False
    is_shared = False

    if trait.type == 'library':
      if trait.preferred_linkage == 'shared':
        is_shared = True
      elif trait.preferred_linkage == 'static':
        is_archive = True
      else:
        assert False, trait.preferred_linkage
    elif trait.type == 'binary':
      pass
    else:
      assert False, trait.type

    if is_archive:
      command = self.expand(self.archiver)
      command.extend(self.expand(self.archiver_out, outfile))
    else:
      command = self.expand(self.linker_cpp if trait.has_cpp_sources() else self.linker_c)
      command.extend(self.expand(self.linker_out, outfile))
      command.extend(self.expand(self.linker_shared if is_shared else self.linker_exe))

    flags = []
    libs = list(trait.syslibs)
    libpath = list()
    for dep in trait.target.dep_traits():
      if isinstance(dep, build):
        libs += dep.exported_syslibs
        if dep.type == 'library':
          additional_input_files.extend(dep.linkname_full or dep.outname_full)
          flags.extend(dep.linker_flags)
      elif isinstance(dep, prebuilt):
        libs += dep.syslibs
        libpath += dep.libpath
        flags.extend(dep.linker_flags)
        if trait.link_style == 'static' and dep.static_libs or not dep.shared_libs:
          additional_input_files.extend(dep.static_libs)
        elif trait.link_style == 'shared' and dep.shared_libs or not dep.static_libs:
          additional_input_files.extend(dep.shared_libs)

    flags += it.concat([self.expand(self.linker_libpath, x) for x in it.unique(libpath)])
    flags += it.concat([self.expand(self.linker_lib, x) for x in it.unique(libs)])
    return command + ['$in'] + flags + additional_input_files

  def set_target_outputs(self, trait, ctx):
    assert isinstance(trait, build)
    outs = trait.outname if trait.is_foreach() else [trait.outname]
    trait.outname_full = [macro.parse(x).eval(ctx, []) for x in outs]
    trait.outname_full = [path.join(trait.target.cell.build_directory, x)
        for x in trait.outname_full]


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

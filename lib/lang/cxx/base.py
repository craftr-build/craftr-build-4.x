"""
Base classes for implementing compilers.
"""

__all__ = [
  'infer_linkage',
  'infer_debug',
  'CxxBuild',
  'CxxPrebuilt',
  'CxxRunTarget',
  'CompilerOptions',
  'Compiler',
  'extmacro'
]

from typing import List, Dict, Union, Callable, Type
import craftr from 'craftr'
import {it, log, macro, path, types} from 'craftr/utils'


def infer_linkage(target):
  choices = set()
  for data in target.dependent_impls().of_type(CxxBuild):
    choices.add(data.link_style)
  if len(choices) > 1:
    log.warn('Target "{}" has preferred_linkage=any, but dependents '
      'specify conflicting link_styles {}. Falling back to static.'
      .format(target.long_name, choices))
    preferred_linkage = 'static'
  elif len(choices) == 1:
    preferred_linkage = choices.pop()
  else:
    preferred_linkage = craftr.session.config.get('cxx.preferred_linkage', 'static')
    if preferred_linkage not in ('static', 'shared'):
      raise RuntimeError('invalid cxx.preferred_linkage option: {!r}'
        .format(preferred_linkage))
  return preferred_linkage


def infer_debug(target):
  for data in target.dependent_impls().of_type(CxxBuild):
    if data.debug:
      return True
  else:
    return False


class CxxBuild(craftr.target.TargetData):

  def __init__(self,
               type: str,
               srcs: List[str] = None,
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
               options: Dict = None):
    if type not in ('library', 'binary'):
      raise ValueError('invalid type: {!r}'.format(type))
    if optimize not in (None, 'speed', 'size'):
      raise ValueError('invalid value for optimize: {!r}'.format(optimize))
    if not link_style:
      link_style = craftr.session.config.get('cxx.link_style', 'static')
    if link_style not in ('static', 'shared'):
      raise ValueError('invalid link_style: {!r}'.format(link_style))
    if preferred_linkage not in ('any', 'static', 'shared'):
      raise ValueError('invalid preferred_linkage: {!r}'.format(preferred_linkage))
    if unity_build is None:
      unity_build = bool(craftr.session.config.get('cxx.unity_build', False))
    if isinstance(srcs, str):
      srcs = [srcs]
    if options is None:
      options = {}
    if isinstance(options, dict):
      options = compiler.options_class(**options)
    if not isinstance(options, compiler.options_class):
      raise TypeError('options must be None, dict or {}, got {} instead'
        .format(compilre.options_class.__name__, type(options).__name__))
    self.srcs = [craftr.localpath(x) for x in (srcs or [])]
    self.type = type
    self.debug = debug
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

    # Set after translate().
    self.outname_full = None
    # Required for MSVC because the file to link with is different
    # than the actual output DLL output file.
    self.linkname_full = None

  def is_staticlib(self):
    return self.type == 'library' and self.preferred_linkage == 'static'

  def is_sharedlib(self):
    return self.type == 'library' and self.preferred_linkage == 'shared'

  def is_binary(self):
    return self.type == 'binary'

  def mounted(self, target):
    super().mounted(target)
    if self.options.__unknown_options__:
      log.warn('[{}]: Unknown compiler option(s): {}'.format(
        target.long_name, ', '.join(self.options.__unknown_options__.keys())))

  def translate(self, target):
    # Update the preferred linkage of this target.
    if self.preferred_linkage == 'any':
      self.preferred_linkage = infer_linkage(target)
    assert self.preferred_linkage in ('static', 'shared')

    # Inherit the debug option if it is not set.
    # XXX What do to on different values?
    if self.debug is None:
      self.debug = infer_debug(target)

    # Inherit the optimize flag if it is not set.
    # XXX What do to on different values?
    if self.optimize is None:
      for data in target.dependents().attr('data').of_type(CxxBuild):
        if data.optimize:
          self.optimize = data.optimize
          break
      else:
        self.optimize = craftr.session.config.get('cxx.optimize', 'speed')
      if self.optimize not in ('speed', 'size'):
        raise RuntimeError('[{}] invalid optimize: {!r}'.format(
          target.long_name, self.optimize))

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
        unity_filename = path.join(target.cell.builddir, 'unity-source-' + self.target.name + suffix)
        path.makedirs(path.dir(unity_filename), exist_ok=True)
        with open(unity_filename, 'w') as fp:
          for filename in srcs:
            print('#include "{}"'.format(path.abs(filename)), file=fp)
        srcs[:] = [unity_filename]

    ctx = macro.Context()
    self.compiler.init_macro_context(target, ctx)
    self.compiler.set_target_outputs(target, ctx)
    assert self.outname_full is not None, 'compiler.set_target_outputs() did not set outname_full'

    # Compile object files.
    obj_dir = path.join(target.cell.builddir, 'obj', target.name)
    obj_files = []
    obj_actions = []
    obj_suffix = macro.parse('$(obj)').eval(ctx, [])

    for lang, srcs in (('c', c_srcs), ('cpp', cpp_srcs)):
      if not srcs: continue
      command = self.compiler.build_compile_flags(target, lang)
      for filename in srcs:
        # XXX Could result in clashing object file names!
        objfile = path.join(obj_dir, path.base(path.rmvsuffix(filename)) + obj_suffix)
        command.extend(self.compiler.build_compile_out_flags(target, lang, objfile))
        command.append(filename)
        obj_actions.append(craftr.actions.System.new(
          target,
          commands = [command],
          environ = self.compiler.compiler_env,
          input_files = [filename],
          output_files = [objfile]
        ))
        obj_files.append(objfile)

    if obj_files:
      additional_input_files = []
      command = self.compiler.build_link_flags(target, self.outname_full, additional_input_files)
      command.extend(obj_files)
      craftr.actions.System.new(
        target,
        commands = [command],
        deps = obj_actions,
        environ = self.compiler.linker_env,
        input_files = obj_files + additional_input_files,
        output_files = [self.outname_full]
      )


class CxxPrebuilt(craftr.target.TargetData):

  def __init__(self,
               includes: List[str] = None,
               defines: List[str] = None,
               static_libs: List[str] = None,
               shared_libs: List[str] = None,
               compiler_flags: List[str] = None,
               linker_flags: List[str] = None,
               syslibs: List[str] = None,
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
    self.preferred_linkage = preferred_linkage

  def translate(self, target):
    pass


class CxxRunTarget(craftr.Gentarget):

  def __init__(self, target_to_run, argv, **kwargs):
    super().__init__(commands=[], **kwargs)
    assert isinstance(target_to_run.data, CxxBuild)
    self.target_to_run = target_to_run
    self.argv = argv

  def translate(self, target):
    assert self.target_to_run.is_translated(), self.target_to_run
    self.commands = [
      [self.target_to_run.data.outname_full] + list(self.argv)
    ]
    super().translate(target)


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

  name: str
  version: str
  options_class: Type[CompilerOptions]

  compiler_c: List[str]               # Arguments to invoke the C compiler.
  compiler_cpp: List[str]             # Arguments to invoke the C++ compiler.
  compiler_env: Dict[str, str]        # Environment variables for the compiler.
  compiler_out: List[str]             # Specify the compiler object output file.

  debug_flag: List[str]               # Flag(s) to enable debug symbols.
  define_flag: str                    # Flag to define a preprocessor macro.
  include_flag: str                   # Flag to specify include directories.
  expand_flag: List[str]              # Flag(s) to request macro-expanded source.
  warnings_flag: List[str]            # Flag(s) to enable all warnings.
  warnings_as_errors_flag: List[str]  # Flag(s) to turn warnings into errors.
  optimize_speed_flag: List[str]
  optimize_size_flag: List[str]

  linker: List[str]                   # Arguments to invoke the linker.
  linker_env: Dict[str, str]          # Environment variables for the binary linker.
  linker_out: List[str]               # Specify the linker output file.
  linker_shared: List[str]            # Flag(s) to link a shared library.
  linker_exe: List[str]               # Flag(s) to link an executable binary.
  # XXX support MSVC /WHOLEARCHIVE
  # XXX support Uninx -fPIC

  archiver: List[str]                 # Arguments to invoke the archiver.
  archiver_env: List[str]             # Environment variables for the archiver.
  archiver_out: List[str]             # Flag(s) to specify the output file.

  lib_macro: Union[str, Callable[[List[str]], str]] = None
  ext_lib_macro: Union[str, Callable[[List[str]], str]] = None
  ext_dll_macro: Union[str, Callable[[List[str]], str]] = None
  ext_exe_macro: Union[str, Callable[[List[str]], str]] = None
  obj_macro: Union[str, Callable[[List[str]], str]] = None

  def __repr__(self):
    return '<{} name={!r} version={!r}>'.format(type(self).__name__, self.name, self.version)

  def expand(self, args, value=None):
    if isinstance(args, str):
      args = [args]
    if value is not None:
      result = [x.replace('%ARG%', value) for x in args]
      if result == args:
        result.append(value)
      return result
    return list(args)

  def init_macro_context(self, target, ctx):
    if self.lib_macro and target.data.type == 'library':
      ctx.define('lib', self.lib_macro)
    if target.data.type == 'library':
      if target.data.preferred_linkage == 'static':
        ext_macro = self.ext_lib_macro
      elif target.data.preferred_linkage == 'shared':
        ext_macro = self.ext_dll_macro
      else:
        assert False, target.data.preferred_linkage
    elif target.data.type == 'binary':
      ext_macro = self.ext_exe_macro
    else:
      assert False, target.data.type
    if ext_macro:
      ctx.define('ext', ext_macro)
    if self.obj_macro:
      ctx.define('obj', self.obj_macro)
    ctx.define('name', target.name)

  def build_compile_flags(self, target, language):
    """
    Build the compiler flags. Does not include the #compiler_out argument,
    yet. Use the #build_compile_out_flags() method for that. The *target* must
    be a #CxxBuild target.
    """

    data = target.data
    assert isinstance(data, CxxBuild)
    assert data.preferred_linkage in ('static', 'shared')

    defines = list(data.defines) + list(data.exported_defines)
    if data.type == 'library' and data.preferred_linkage == 'shared':
      defines += list(data.shared_defines) + list(data.exported_shared_defines)
    else:
      defines += list(data.static_defines) + list(data.exported_static_defines)

    includes = list(data.includes) + list(data.exported_includes)
    flags = list(data.compiler_flags) + list(data.exported_compiler_flags)
    for dep in target.impls():
      if isinstance(dep, CxxBuild):
        includes.extend(dep.exported_includes)
        defines.extend(dep.exported_defines)
        flags.extend(dep.exported_compiler_flags)
        if dep.type == 'library' and dep.preferred_linkage == 'shared':
          defines.extend(dep.exported_shared_defines)
        else:
          defines.extend(dep.exported_static_defines)
      elif isinstance(dep, CxxPrebuilt):
        includes.extend(dep.includes)
        defines.extend(dep.defines)
        flags.extend(dep.compiler_flags)

    command = self.expand(getattr(self, 'compiler_' + language))
    for include in includes:
      command.extend(self.expand(self.include_flag, include))
    for define in defines:
      command.extend(self.expand(self.define_flag, define))
    command.extend(flags)

    if data.warnings:
      command.extend(self.expand(self.warnings_flag))
    if data.warnings_as_errors:
      command.extend(self.expand(self.warnings_as_errors))
    if not data.debug:
      command += self.expand(getattr(self, 'optimize_' + data.optimize + '_flag'))

    return command

  def build_compile_out_flags(self, target, language, objfile):
    return self.expand(self.compiler_out, objfile)

  def build_link_flags(self, target, outfile, additional_input_files):
    assert isinstance(additional_input_files, list)
    is_archive = False
    is_shared = False

    data = target.data
    if data.type == 'library':
      if data.preferred_linkage == 'shared':
        is_shared = True
      elif data.preferred_linkage == 'static':
        is_archive = True
      else:
        assert False, data.preferred_linkage
    elif data.type == 'binary':
      pass
    else:
      assert False, data.type

    if is_archive:
      command = self.expand(self.archiver)
      command.extend(self.expand(self.archiver_out, outfile))
    else:
      command = self.expand(self.linker)
      command.extend(self.expand(self.linker_out, outfile))
      command.extend(self.expand(self.linker_shared if is_shared else self.linker_exe))

    flags = []
    libs = set(data.syslibs)
    for dep in target.impls():
      if isinstance(dep, CxxBuild):
        libs |= set(dep.exported_syslibs)
        if dep.type == 'library':
          additional_input_files.append(dep.linkname_full or dep.outname_full)
          flags.extend(dep.linker_flags)
      elif isinstance(dep, CxxPrebuilt):
        libs |= set(dep.syslibs)
        flags.extend(dep.linker_flags)
        if data.link_style == 'static' and dep.static_libs or not dep.shared_libs:
          additional_input_files.extend(dep.static_libs)
        elif data.link_style == 'shared' and dep.shared_libs or not dep.static_libs:
          additional_input_files.extend(dep.shared_libs)

    flags += it.concat([self.expand(self.linker_lib, x) for x in libs])
    return command + flags + additional_input_files

  def set_target_outputs(self, target, ctx):
    assert isinstance(target.data, CxxBuild)
    target.data.outname_full = macro.parse(target.data.outname).eval(ctx, [])
    target.data.outname_full = path.join(target.cell.builddir, target.data.outname_full)


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
  def compiled_extmacro(ctx, args):
    if args and args[0]:
      return with_version.eval(ctx, args)
    else:
      return without_version.eval(ctx, args)

  return compiled_extmacro

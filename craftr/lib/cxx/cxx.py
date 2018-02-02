
import craftr
from craftr import path

# TODO: Support precompiled headers.
# TODO: Support compiler-wrappers like ccache.
# TODO: Support linker-wrappers (eg. for coverage).

class CxxTargetHandler(craftr.TargetHandler):

  def __init__(self, toolchain=None):
    toolchain, fragment = (toolchain or options.toolchain).partition('#')[::2]
    self.toolchain = toolchain
    self.compiler = load('./impl/' + toolchain + '.py').get_compiler(fragment)

    print('Selected compiler: {} ({}) {} for {}'.format(
      self.compiler.name, self.compiler.id, self.compiler.version, self.compiler.arch))

  def get_common_property_scope(self):
    return 'cxx'

  def setup_target(self, target):
    # Largely inspired by the Qbs cpp module.
    # https://doc.qt.io/qbs/cpp-module.html

    # General
    # =======================

    # Specifies the target type. Either `executable` or `library`.
    target.define_property('cxx.type', 'String', 'executable')

    # The C and/or C++ input files for the target. If this property is not
    # set, the target will not be considered a C/C++ build target.
    target.define_property('cxx.srcs', 'StringList')

    # Allow the link-step to succeed even if symbols are unresolved.
    target.define_property('cxx.allowUnresolvedSymbols', 'Bool', False)

    # Combine C/C++ sources into a single translation unit. Note that
    # many projects can not be compiled in this fashion.
    target.define_property('cxx.combineCSources', 'Bool', False)
    target.define_property('cxx.combineCppSources', 'Bool', False)

    # Allow the linker to discard data that appears to be unused.
    # This value being undefined uses the linker's default.
    target.define_property('cxx.discardUnusedData', 'Bool')

    # Whether to store debug information in an external file or bundle
    # instead of within the binary. Defaults to True for MSVC, False
    # otherwise.
    target.define_property('cxx.separateDebugInformation', 'Bool')

    # Preprocessor definitions to set when compiling.
    target.define_property('cxx.defines', 'StringList')
    target.define_property('cxx.definesForStaticBuild', 'StringList')
    target.define_property('cxx.definesForSharedBuild', 'StringList')

    # Include search paths.
    target.define_property('cxx.includes', 'StringList')

    # Library search paths.
    target.define_property('cxx.libraryPaths', 'StringList')

    # Paths for the dynamic linker. This is only used when running
    # the product of a build target via Craftr.
    target.define_property('cxx.runPaths', 'StringList')

    # Dynamic libraries to link. You should use target dependencies
    # wherever possible rather than using this property.
    target.define_property('cxx.dynamicLibraries', 'StringList')

    # Static libraries to link. You should use target dependencies
    # wherever possible rather than using this property.
    target.define_property('cxx.staticLibraries', 'StringList')

    # List of files to automatically include at the beginning of
    # each translation unit.
    target.define_property('cxx.prefixHeaders', 'StringList')

    # Optimization level. Valid values are `none`, `size` and `speed`.
    target.define_property('cxx.optimization', 'String')

    # Whether to treat warnings as errors.
    target.define_property('cxx.treatWarningsAsErrors', 'Bool')

    # Specifies the warning level. Valid values are `none` or `all`.
    target.define_property('cxx.warningLevel', 'String')

    # Flags that are added to all compilation steps, independent of
    # the language.
    target.define_property('cxx.compilerFlags', 'StringList')

    # Specifies the way the library prefers to be linked. Either 'static' or 'dynamic'.
    target.define_property('cxx.preferredLinkage', 'String')

    # Flags that are added to C compilation.
    target.define_property('cxx.cFlags', 'String')

    # Flags that are added to C++ compilation.
    target.define_property('cxx.cppFlags', 'String')

    # The version of the C standard. If left undefined, the compiler's
    # default value is used. Valid values include `c89`, `c99` and `c11`.
    target.define_property('cxx.cStd', 'String')

    # The C standard library to link to.
    target.define_property('cxx.cStdlib', 'String')

    # The version of the C++ standard. If left undefined, the compiler's
    # default value is used. Valid values include `c++98`, `c++11`
    # and `c++14`.
    target.define_property('cxx.cppStd', 'String')

    # The C++ standard library to link to. Possible values are `libc++`
    # and `libstdc++`.
    target.define_property('cxx.cppStdlib', 'String')

    # Additional flags for the linker.
    target.define_property('cxx.linkerFlags', 'StringList')

    # Name of the entry point of an executable or dynamic library.
    target.define_property('cxx.entryPoint', 'String')

    # Type of the runtime library. Accepted values are `dynamic` and
    # `static`. Defaults to `dynamic` for MSVC, otherwise undefined.
    # For GCC/Clang, `static` will imply `-static-libc` or flags alike.
    target.define_property('cxx.runtimeLibrary', 'String')

    # Whether to enable exception handling.
    target.define_property('cxx.enableExceptions', 'Bool', True)

    # Whether to enable runtime type information
    target.define_property('cxx.enableRtti', 'Bool', True)

    # Apple Settings
    # =======================

    # Additional search paths for OSX frameworks.
    target.define_property('cxx.frameworkPaths', 'StringList')

    # OSX framework to link. If the framework is part of your project,
    # consider using a dependency instead.
    target.define_property('cxx.frameworks', 'StringList')

    # OSX framework to link weakly. If the framework is part of your project,
    # consider using a dependency instead.
    target.define_property('cxx.weakFrameworks', 'StringList')

    # A version number in the format [major] [minor] indicating the earliest
    # version that the product should run on.
    target.define_property('cxx.minimumMacosVersion', 'String')

    # Unix Settings
    # =======================

    # Generate position independent code. If this is undefined, PIC is
    # generated for libraries, but not applications.
    target.define_property('cxx.positionIndependentCode', 'Bool')

    # rpaths that are passed to the linker. Paths that also appear
    # in runPaths are ignored.
    target.define_property('cxx.rpaths', 'StringList')

    # The version to be appended to the soname in ELF shared libraries.
    target.define_property('cxx.soVersion', 'String')

    # Visibility level for exported symbols. Possible values incliude
    # `default`, `hidden`, `hiddenInlines` and `minimal (which combines
    # `hidden` and `hiddenInlines`).
    target.define_property('cxx.visibility', 'String')

    # Windows Settings
    # =======================

    # Whether to automatically generate a manifest file and include it in
    # the binary. Disable this property if you define your own .rc file.
    target.define_property('cxx.generateManifestFile', 'Bool', True)

    # Specifies the character set used in the Win32 API. Defaults to
    # "unicode".
    target.define_property('cxx.windowsApiCharacterSet', 'String')

    # Advanced Settings
    # =======================

    # TODO

    # Map of defines by language name.
    #target.define_property('cxx.definesByLanguage', 'Map[String, Map[String]]')

    # Map of defines by compiler ID.
    #target.define_property('cxx.definesByCompiler', 'Map[String, Map[String]]')

    # Map of defines by platform ID.
    #target.define_property('cxx.definesByPlatform', 'Map[String, Map[String]]')

    # Save temporary build prodcuts. Note that some toolchains (such as MSVC)
    # can not compile AND actually build at the same time.
    target.define_property('cxx.saveTemps', 'Bool', False)

    self.compiler.setup_target(target)

  def setup_dependency(self, dep):
    # If False, the dependency will not be linked, even if it is a valid
    # input for a linker rule. This property affects library dependencies only.
    dep.define_property('cxx.link', 'Bool', True)

    # If True, then if the dependency is a static library, all of its
    # objects will be pulled into a target binary, even if their symbols
    # appear to be unused. This parameter is mainly useful when creating
    # a dynamic library from static libraries.
    dep.define_property('cxx.linkWholeArchive', 'Bool', False)

  def finalize_target(self, target, data):
    src_dir = target.directory()
    build_dir = path.join(context.build_directory, target.module().name())

    data.srcs = [path.canonical(x, src_dir) for x in data.srcs]
    data.includes = [path.canonical(x, src_dir) for x in data.includes]
    data.prefixHeaders = [path.canonical(x, src_dir) for x in data.prefixHeaders]

    # TODO: Determine whether we build an executable, static library
    #       or shared library.
    data.productFilename = target.name() + '-' + target.module().version()
    target.outputs().add(data.productFilename, ['exe'])

  def translate_target(self, target, data):

    c_srcs = []
    cpp_srcs = []
    for filename in data.srcs:
      if filename.endswith('.c'): c_srcs.append(filename)
      if filename.endswith('.cpp') or filename.endswith('.cc'):
        cpp_srcs.append(filename)

    compile_actions = []
    obj_files = []
    for (srcs, lang) in ((c_srcs, 'c'), (cpp_srcs, 'cpp')):
      if not srcs: continue
      command = self.compiler.build_compile_flags(lang, target, data)
      action = target.add_action('cxx.compile' + lang.capitalize(),
        environ=self.compiler.compiler_env, commands=[command], input=True)
      for src in srcs:
        build = action.add_buildset()
        build.files.add(src, ['in', 'src', 'src.' + lang])
        self.compiler.update_compile_buildset(build, target, data)
        obj_files += build.files.tagged('out', 'obj')
      compile_actions.append(action)

    link_action = None
    if obj_files:
      command = self.compiler.build_link_flags('cpp' if cpp_srcs else 'c', target, data)
      link_action = target.add_action('cxx.link', commands=[command],
        environ=self.compiler.linker_env, deps=compile_actions)
      build = link_action.add_buildset()
      build.files.add(obj_files, ['in', 'obj'])
      build.files.add(data.productFilename, ['out', 'product'])
      self.compiler.update_link_buildset(build, target, data)

    if link_action and data.type == 'executable':
      command = [data.productFilename]
      action = target.add_action('cxx.run', commands=[command],
        explicit=True, syncio=True, output=False)
      action.add_buildset()


module.register_target_handler(CxxTargetHandler())

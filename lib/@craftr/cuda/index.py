
import os, sys
import craftr, {path, utils.stream.concat as concat} from 'craftr'
import cxx from '@craftr/cxx'
import gcc from '@craftr/cxx/gcc'
import msvc from '@craftr/cxx/msvc'

sdk_dir = craftr.options.get('cuda.sdk_dir', os.environ.get('CUDA_PATH'))
if not sdk_dir:
  raise EnvironmentError('cuda.sdk_dir or CUDA_PATH is not set')
static = craftr.options.get('cuda.static', True)

compiler_env = {}
if sys.platform.startswith('win32'):
  if cxx.compiler.id == 'msvc':
    compiler_env = cxx.compiler.compiler_env
  else:
    compiler_env = msvc.MsvcToolkit.from_config().environ


class NvccCompilerOptions(gcc.GccCompilerOptions):

  __annotations__ = []


class NvccCompiler(gcc.GccCompiler):

  options_class = NvccCompilerOptions

  id = 'nvcc'
  name = 'NVIDIA CUDA Compiler'
  arch = 'x64'  # TODO
  version = '??'  # TODO

  compiler_c = 'nvcc'
  compiler_cpp = 'nvcc'
  linker_c = 'nvcc'
  linker_cpp = 'nvcc'
  linker_runtime = {
    'c': {'static': ['--cudart', 'static'], 'dynamic': ['--cudart', 'shared']},
    'cpp': {'static': ['--cudart', 'static'], 'dynamic': ['--cudart', 'shared']},
  }

  if os.name == 'nt':
    compiler_env = compiler_env.copy()
    compiler_env['PATH'] = path.join(sdk_dir, 'bin') + os.pathsep + compiler_env['PATH']
    linker_env = compiler_env
    archiver_env = compiler_env
    depfile_args = None
    depfile_name = None
    deps_prefix = cxx.compiler.deps_prefix

    for name in ('archiver', 'archiver_out', 'lib_macro', 'ext_lib_macro', 'ext_dll_macro', 'ext_exe_macro', 'obj_macro'):
      locals()[name] = getattr(msvc.MsvcCompiler, name)

    def build_compile_flags(self, build, language):
      compiler_options = ['/showIncludes']
      if build.static_runtime:
        compiler_options += ['/MTd' if build.debug else '/MT']
      else:
        compiler_options += ['/MDd' if build.debug else '/MD']

      flags = super().build_compile_flags(build, language)
      flags += concat([('-Xcompiler', x) for x in compiler_options])
      return flags

    def build_link_flags(self, build, outfile, additional_input_files):
      # It appears as if CUDA, at least in a debug build, adds LIBCMT which
      # will then conflict with LIBCMTD.
      if build.static_runtime:
        linker_options = ['/NODEFAULTLIB:LIBCMT'] if build.debug else ['/NODEFAULTLIB:LIBCMTD']
      else:
        linker_options = ['/NODEFAULTLIB:MSVCRT'] if build.debug else ['/NODEFAULTLIB:MSVCRTD']

      flags = super().build_link_flags(build, outfile, additional_input_files)
      flags += concat([('-Xlinker', x) for x in linker_options])
      return flags


compiler = NvccCompiler()
build = craftr.Factory(cxx.CxxBuild, compiler=compiler)
library = craftr.Factory(cxx.CxxBuild, type='library', compiler=compiler)
binary = craftr.Factory(cxx.CxxBuild, type='binary', compiler=compiler)
embed = craftr.Factory(cxx.CxxEmbed, library_factory=library)
prebuild = craftr.Factory(cxx.CxxPrebuilt)
run = cxx.run


import {MingwInstallation} from 'craftr/tools/mingw'
import {GccCompiler} from './gcc'
import {extmacro} from '.'


class MingwCompilerOptions(GccCompiler.options_class):

  gcc_static_runtime = True


class MingwCompiler(GccCompiler):

  name = 'mingw'
  options_class = MingwCompilerOptions
  ext_exe_macro = extmacro('.exe', '.$(0).exe')


def get_compiler(fragment):
  index = 0
  if fragment:
    index = int(fragment)
  inst = MingwInstallation.list()[index]
  env = inst.environ()
  return MingwCompiler(
    compiler_env=inst.environ(),
    linker_env=inst.environ(),
    archiver_env=inst.environ()
  )

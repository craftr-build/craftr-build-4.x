
import {MingwInstallation} from 'craftr/tools/mingw'
import {GccCompiler} from './gcc'
import {extmacro} from '.'



class MingwCompiler(GccCompiler):

  name = 'mingw'
  ext_exe_macro = extmacro('.exe', '.$(0).exe')

  def __init__(self, mingw, **kwargs):
    super().__init__(**kwargs)
    self.mingw = mingw


def get_compiler(fragment):
  if fragment:
    try:
      index = int(fragment)
    except ValueError:
      inst = MingwInstallation(fragment, None)
    else:
      inst = MingwInstallation.list()[index]
  else:
    inst = MingwInstallation.list()[0]

  print('MinGW {} (gcc-{} v{}) @ {}'.format('x64' if inst.is_64 else 'x86',
      inst.gccinfo['target'], inst.gccinfo['version'], inst.binpath))

  return MingwCompiler(
    inst,
    compiler_env=inst.environ,
    linker_env=inst.environ,
    archiver_env=inst.environ
  )

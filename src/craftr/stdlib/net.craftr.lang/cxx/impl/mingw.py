
import {MingwInstallation} from 'net.craftr.compiler.mingw'
import {GccCompiler} from './gcc'


class MingwCompiler(GccCompiler):

  id = 'mingw'
  name = 'MinGW'
  family = 'gcc'

  executable_suffix = '.exe'
  library_prefix = ''
  library_shared_suffix = '.dll'
  library_static_suffix = '.lib'

  def __init__(self, mingw, **kwargs):
    kwargs.setdefault('arch', 'x64' if mingw.is_64 else 'x86')
    super().__init__(**kwargs)
    self.mingw = mingw

  def info_string(self):
    return 'MinGW {} (gcc-{} v{}) from "{}"'.format(
      'x64' if self.mingw.is_64 else 'x86',
      self.mingw.gccinfo['target'],
      self.mingw.gccinfo['version'],
      self.mingw.install_dir)


def get_compiler(fragment):
  if fragment:
    try:
      index = int(fragment)
    except ValueError:
      inst = MingwInstallation(fragment)
    else:
      inst = MingwInstallation.list()[index]
  else:
    inst = MingwInstallation.list()[0]

  return MingwCompiler(
    inst,
    compiler_env=inst.environ,
    linker_env=inst.environ,
    archiver_env=inst.environ
  )

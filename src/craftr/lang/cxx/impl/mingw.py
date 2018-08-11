
import _gcc from './gcc'

class MingwCompiler(_gcc.GccCompiler):

  executable_suffix = '.exe'


def get_compiler(fragment):
  return _gcc.get_compiler(fragment, MingwCompiler)


import {GccCompiler} from './gcc'

class LlvmCompiler(GccCompiler):

  id = 'llvm'
  name = 'llvm'

  compiler_c = 'clang'
  compiler_cpp = 'clang++'
  linker_c = compiler_c
  linker_cpp = compiler_cpp


def get_compiler(fragment):
  return LlvmCompiler()

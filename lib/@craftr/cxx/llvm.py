
import {GccCompiler} from './gcc'
import {extmacro} from '.'

# TODO: Select correct file extensions on Linux/macOS.

class LlvmCompiler(GccCompiler):

  id = 'llvm'
  name = 'llvm'

  compiler_c = 'clang'
  compiler_cpp = 'clang++'
  linker_c = compiler_c
  linker_cpp = compiler_cpp

  ext_dll_macro = extmacro('.dylib', '.dylib.$(0)')



def get_compiler(fragment):
  return LlvmCompiler()

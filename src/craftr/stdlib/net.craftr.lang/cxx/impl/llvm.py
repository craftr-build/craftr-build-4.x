
import os
import {GccCompiler} from './gcc'
import {LlvmInstallation} from 'net.craftr.compiler.llvm'
from craftr.api import OS, path


class LlvmCompiler(GccCompiler):

  id = 'llvm'
  name = 'LLVM'
  family = 'gcc'

  compiler_c = ['clang']
  compiler_cpp = ['clang++']
  linker_c = compiler_c
  linker_cpp = compiler_cpp


def get_compiler(fragment):
  if OS.id == 'win32':
    inst = next((LlvmInstallation.iter_installations()), None)
    if not inst:
      error('No Windows LLVM installation found.')
    return LlvmCompiler(compiler_env=inst.environ, linker_env=inst.environ)
  else:
    return LlvmCompiler()

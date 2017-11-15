
import {log} from 'craftr/utils'
import _msvc from 'craftr/lang/msvc'
import {BaseCompiler} from './base'

class MsvcCompiler(BaseCompiler):
  pass


def get_compiler(fragment):
  if fragment:
    log.warn('craftr/lang/cxx/msvc: Fragment not supported. (fragment = {!r})'
      .format(fragment))
  return MsvcCompiler()

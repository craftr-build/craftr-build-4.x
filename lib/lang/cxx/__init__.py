
import sys
import typing as t
import craftr from 'craftr'
import {log, path} from 'craftr/utils'
import * from './base'


def _load_compiler():
  name = craftr.session.config.get('cxx.compiler', None)
  if name is None:
    if sys.platform.startswith('win32'):
      name = 'msvc'
    elif sys.platform.startswith('darwin'):
      name = 'llvm'
    else:
      name = 'gcc'

  name, fragment = name.partition(':')[::2]
  module = require.try_('./' + name, name)
  return module.get_compiler(fragment)


compiler = _load_compiler()
embed = craftr.target_factory(CxxEmbedFiles)
build = craftr.target_factory(CxxBuild)
prebuilt = craftr.target_factory(CxxPrebuilt)


def run(target, *argv, name=None, **kwargs):
  target = craftr.T(target)
  if not name:
    name = target.name + '_run'
  return craftr.target_factory(CxxRunTarget)(
    name = name,
    deps = [target],
    target_to_run = target,
    argv = argv,
    **kwargs
  )


@build.preprocess
@embed.preprocess
def _build_preprocess(kwargs):
  kwargs.setdefault('compiler', compiler)

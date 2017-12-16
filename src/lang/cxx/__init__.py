
import functools
import logging as log
import sys
import typing as t

import craftr from 'craftr'
import path from 'craftr/utils/path'
import {build, prebuilt, run as _run, embed} from './base'


def _load_compiler():
  name = craftr.options.get('cxx.compiler', None)
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
library = functools.partial(build, type='library')
binary = functools.partial(build, type='binary')


def run(target, *argv, name=None, **kwargs):
  target = craftr.resolve_target(target)
  if not name:
    name = target.name + '_run'
  return _run(
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

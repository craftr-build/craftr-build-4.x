
import sys
import typing as t
import craftr from 'craftr'
import {path} from 'craftr/utils'

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


class CxxLibrary(craftr.target.TargetData):

  def __init__(self,
               srcs: t.List[str],
               target: str,
               includes: t.List[str] = None,
               exported_includes: t.List[str] = None,
               defines: t.List[str] = None,
               exported_defines: t.List[str] = None,
               compiler_flags: t.List[str] = None,
               exported_compiler_flags: t.List[str] = None,
               linker_flags: t.List[str] = None,
               exported_linker_flags: t.List[str] = None,
               link_style: str = None,
               preferred_linkage: str = 'any',
               libname: str = None,
               unity_build: bool = None):
    if target not in ('library', 'binary'):
      raise ValueError('invalid target: {!r}'.format(target))
    if not link_style:
      link_style = craftr.session.config.get('cxx.link_style', 'static')
    if link_style not in ('static', 'shared'):
      raise ValueError('invalid link_style: {!r}'.format(link_style))
    if preferred_linkage not in ('any', 'static', 'shared'):
      raise ValueError('invalid preferred_linkage: {!r}'.format(preferred_linkage))
    if unity_build is None:
      unity_build = bool(craftr.session.config.get('cxx.unity_build', False))
    self.srcs = [craftr.localpath(x) for x in srcs]
    self.target = target
    self.includes = [craftr.localpath(x) for x in (includes or [])]
    self.exported_includes = [craftr.localpath(x) for x in (exported_includes or [])]
    self.defines = defines or []
    self.exported_defines = exported_defines or []
    self.compiler_flags = compiler_flags or []
    self.exported_compiler_flags = exported_compiler_flags or []
    self.linker_flags = linker_flags or []
    self.exported_linker_flags = exported_linker_flags or []
    self.link_style = link_style
    self.preferred_linkage = preferred_linkage
    self.libname = libname
    self.unity_build = unity_build

  def translate(self, target):
    raise NotImplementedError


class CxxPrebuilt(craftr.target.TargetData):

  def __init__(self,
               includes: t.List[str] = None,
               defines: t.List[str] = None,
               static_libs: t.List[str] = None,
               static_pic_libs: t.List[str] = None,
               shared_libs: t.List[str] = None,
               compiler_flags: t.List[str] = None,
               linker_flags: t.List[str] = None,
               preferred_linkage: t.List[str] = 'any'):
    if preferred_linkage not in ('any', 'static', 'shared'):
      raise ValueError('invalid preferred_linkage: {!r}'.format(preferred_linkage))
    self.includes = [craftr.localpath(x) for x in (includes or [])]
    self.defines = defines or []
    self.static_libs = static_libs or []
    self.static_pic_libs = static_pic_libs or []
    self.shared_libs = shared_libs or []
    self.compiler_flags = compiler_flags or []
    self.linker_flags = linker_flags or []
    self.preferred_linkage = preferred_linkage

  def translate(self, target):
    raise NotImplementedError


compiler = _load_compiler()
library = craftr.target_factory(CxxLibrary)
prebuilt = craftr.target_factory(CxxPrebuilt)

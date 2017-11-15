
import sys
import typing as t
import craftr from 'craftr'
import {log, path} from 'craftr/utils'

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


class CxxBuild(craftr.target.TargetData):

  def __init__(self,
               type: str,
               srcs: t.List[str] = None,
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
               outname: str = '$(lib)$(name)$(ext)',
               unity_build: bool = None):
    if type not in ('library', 'binary'):
      raise ValueError('invalid type: {!r}'.format(type))
    if not link_style:
      link_style = craftr.session.config.get('cxx.link_style', 'static')
    if link_style not in ('static', 'shared'):
      raise ValueError('invalid link_style: {!r}'.format(link_style))
    if preferred_linkage not in ('any', 'static', 'shared'):
      raise ValueError('invalid preferred_linkage: {!r}'.format(preferred_linkage))
    if unity_build is None:
      unity_build = bool(craftr.session.config.get('cxx.unity_build', False))
    if isinstance(srcs, str):
      srcs = [srcs]
    self.srcs = [craftr.localpath(x) for x in (srcs or [])]
    self.type = type
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
    self.outname = outname
    self.unity_build = unity_build

    self.outname_full = None

  def translate(self, target):
    # Update the preferred linkage of this target.
    if self.preferred_linkage == 'any':
      choices = set()
      for data in target.dependents().attr('data').of_type(CxxBuild):
        choices.add(data.link_style)
      if len(choices) > 1:
        log.warn('Target "{}" has preferred_linkage=any, but dependents '
          'specify conflicting link_styles {}. Falling back to static.'
          .format(self.long_name, choices))
        self.preferred_linkage = 'static'
      elif len(choices) == 1:
        self.preferred_linkage = choices.pop()
      else:
        self.preferred_linkage = craftr.session.config.get('cxx.preferred_linkage', 'static')
        if self.preferred_linkage not in ('static', 'shared'):
          raise RuntimeError('invalid cxx.preferred_linkage option: {!r}'
            .format(self.preferred_linkage))
    assert self.preferred_linkage in ('static', 'shared')

    # Separate C and C++ sources.
    c_srcs = []
    cpp_srcs = []
    unknown = []
    for src in self.srcs:
      if src.endswith('.cpp') or src.endswith('.cc'):
        cpp_srcs.append(src)
      elif src.endswith('.c'):
        c_srcs.append(src)
      else:
        unknown.append(src)
    if unknown:
      if c_srcs or not cpp_srcs:
        c_srcs.extend(unknown)
      else:
        cpp_srcs.extend(unknown)

    # Create the unity source file(s).
    if self.unity_build:
      for srcs, suffix in ((c_srcs, '.c'), (cpp_srcs, '.cpp')):
        if not srcs or len(srcs) == 1:
          continue
        unity_filename = path.join(target.cell.builddir, 'unity-source-' + self.target.name + suffix)
        path.makedirs(path.dir(unity_filename), exist_ok=True)
        with open(unity_filename, 'w') as fp:
          for filename in srcs:
            print('#include "{}"'.format(path.abs(filename)), file=fp)
        srcs[:] = [unity_filename]

    # Determine the output filename.
    outfile = compiler.get_output_filename(target)
    outfile = path.join(target.cell.builddir, outfile)
    self.outname_full = outfile

    # Determine the output directory for object files.
    obj_dir = path.join(target.cell.builddir, 'obj', target.name)

    session = compiler.create_session()
    session.init_session(target, obj_dir)
    if c_srcs:
      session.compile_c(c_srcs)
    if cpp_srcs:
      session.compile_cpp(cpp_srcs)
    session.link(outfile)


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
    pass


compiler = _load_compiler()
build = craftr.target_factory(CxxBuild)
prebuilt = craftr.target_factory(CxxPrebuilt)

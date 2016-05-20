# -*- mode: python -*-
# Copyright (C) 2016  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

__all__ = ['detect', 'MsvcCompiler', 'MsvcLinker', 'MsvcAr',
  'Compiler', 'Linker', 'Archiver']

from craftr import *
from craftr.ext.compiler import *
from craftr.ext import platform
import os, re, tempfile


@memoize_tool
def detect(program):
  ''' Detects the version of the MSVC compiler from the specified
  *program* name and returns a dictionary with information that can
  be passed to the constructor of `MsvcCompiler` or raises
  `ToolDetectionError`.

  This function also supports detecting the Clang-CL compiler. '''

  ''' Assuming *program* points to a MSVC compiler or Clang-CL compiler,
  this function extracts meta information of the tool. The returned
  dictionary contains the following keys:

  * name (either ``'msvc'`` or ``'clang-cl'``)
  * version
  * version_str
  * target
  * thread_model
  * msvc_deps_prefix

  :raise OSError: If *program* can not be executed (eg. if it does not exist).
  :raise ToolDetectionError: If *program* is not GCC or GCC++. '''

  clang_cl_expr = r'clang\s+version\s+([\d\.]+).*\n\s*target:\s*([\w\-\_]+).*\nthread\s+model:\s*(\w+)'
  msvc_expr = r'compiler\s+version\s*([\d\.]+)\s*for\s*(\w+)'

  # Determine kind and version. We need to do this separately from
  # the /showIncludes detection as Clang CL does not display a logo
  # when being invoked.
  #
  # We can't use the /? option if the actual "program" is a batch
  # script as this will print the help for batch files (Microsoft, pls).
  # MSVC will error on -v, Clang CL will give us good info.
  output = shell.pipe([program, '-v'], shell=True, check=False).output
  match = re.match(clang_cl_expr, output, re.I)
  if match:
    # We've detected a version of Clang CL!
    name = 'clang-cl'
    version = match.group(1)
    arch = match.group(2)
    thread_model = match.group(3)
  else:
    # Extract the MSVC compiler version and architecture.
    match = re.search(msvc_expr, output, re.I)
    if not match:
      raise ToolDetectionError('MSVC version and architecture could not be detected\n\n' + output)

    name = 'msvc'
    version = match.group(1)
    arch = match.group(2)
    thread_model = 'win32'

  # Determine the msvc_deps_prefix by making a small test. The
  # compilation will not succeed since no entry point is defined.
  deps_prefix = None
  with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as fp:
    fp.write(b'#include <stddef.h>\n')
    fp.close()
    command = [program, '/Zs', '/showIncludes', fp.name]
    try:
      output = shell.pipe(command, shell=True, check=False).output
    finally:
      os.remove(fp.name)

    # Find the "Note: including file:" in the current language. We
    # assume that the structure is the same, only the words different.
    # After the logo output follows the filename followed by the include
    # notices.
    for line in output.split('\n'):
      if 'stddef.h' in line:
        match = re.search('[\w\s]+:[\w\s]+:', line)
        if match:
          deps_prefix = match.group(0)

  if not deps_prefix:
    warn('msvc_deps_prefix could not be determined, fallback on english string')
    deps_prefix = 'Note: including file:'

  return {
    'name': name,
    'version': version,
    'version_str': output.split('\n', 1)[0].strip(),
    'target': arch,
    'thread_model': thread_model,
    'msvc_deps_prefix': deps_prefix,
  }


class MsvcCompiler(BaseCompiler):
  ''' Interface for the MSVC compiler. '''

  name = 'msvc'

  def __init__(self, program='cl', language='c', desc=None, **kwargs):
    super().__init__(program=program, language=language, **kwargs)
    if language not in ('c', 'c++'):
      raise ValueError('unsupported language: {0}'.format(language))
    if desc is None:
      desc = detect(program)
    self.desc = desc
    self.name = desc['name']
    self.version = desc['version']
    self.target = desc['target']
    self.deps_prefix = desc['msvc_deps_prefix']

  def __repr__(self):
    res = '<MsvcCompiler language={0!r} deps_prefix={1!r}'.format(
      self.settings['language'], self.deps_prefix)
    if self.version:
      res += ' version={0!r} target={1!r}'.format(self.version, self.target)
    else:
      res += ' (undetermined)'
    return res + '>'

  def compile(self, sources, frameworks=(), target_name=None, meta=None, **kwargs):
    '''
    Supported options:

      * include
      * defines
      * language
      * debug
      * warn
      * optimize
      * exceptions
      * autodeps
      * description
      * program
      * additional_flags
      * msvc_additional_flags
      * msvc_compile_additional_flags

    Unsupported options supported by other compilers:

      * std
      * pedantic
      * pic
      * osx_fwpath
      * osx_frameworks

    Target meta variables: *none*
    '''

    builder = self.builder(sources, frameworks, kwargs, name=target_name, meta=meta)
    objects = gen_objects(builder.inputs, suffix=platform.obj)

    include = utils.unique(builder.merge('include'))
    defines = utils.unique(builder.merge('defines'))
    language = builder['language']
    debug = builder.get('debug', False)
    warn = builder.get('warn', 'all')
    optimize = builder.get('optimize', None)
    exceptions = builder.get('exceptions', None)
    autodeps = builder.get('autodeps', True)
    msvc_runtime_library = builder.get('msvc_runtime_library', None)
    builder.target['description'] = builder.get('description', '{0} Compile Object ($out)'.format(self.name))

    if language not in ('c', 'c++'):
      raise ValueError('invalid language: {0!r}'.format(language))

    command = [builder['program'], '/nologo', '/c', '$in', '/Fo$out']
    command += ['/I' + x for x in include]
    command += ['/D' + x for x in defines]
    if debug:
      command += ['/Od', '/Zi', '/RTC1', '/FC', '/Fd$out.pdb']
      if not self.version or self.version >= 'v18':
        # Enable parallel writes to .pdb files. We also assume that this
        # option is necessary by default.
        command += ['/FS']

    if exceptions:
      if language != 'c++':
        builder.invalid_option('exception', True, cause='not supported in {0!r}'.format(language))
      command += ['/EHsc']
    elif exceptions is None and language == 'c++':
      # Enable exceptions by default.
      command += ['/EHsc']

    if warn == 'all':
      # /Wall really shows too many warnings, /W4 is pretty good.
      command += ['/W4']
    elif warn == 'none':
      command += ['/w']
    elif warn is None:
      pass
    else:
      builder.invalid_option('warn')

    if debug:
      if optimize and optimize != 'debug':
        builder.invalid_option('optimize', cause='no optimize with debug enabled')
    elif optimize == 'speed':
      command += ['/O2']
    elif optimize == 'size':
      command += ['/O1', '/Os']
    elif optimize in ('debug', 'none', None):
      command += ['/Od']
    else:
      builder.invalid_option('optimize')

    if msvc_runtime_library == 'dynamic':
      command += ['/MTd' if debug else '/MT']
    elif msvc_runtime_library == 'static':
      command += ['/MDd' if debug else '/MD']
    elif msvc_runtime_library is not None:
      raise ValueError('invalid msvc_runtime_library: {0!r}'.format(msvc_runtime_library))

    if autodeps:
      builder.target['deps'] = 'msvc'
      builder.target['msvc_deps_prefix'] = self.deps_prefix
      command += ['/showIncludes']
    command += builder.merge('additional_flags')
    command += builder.merge('msvc_additional_flags')
    command += builder.merge('msvc_compile_additional_flags')

    return builder.create_target(command, outputs=objects, foreach=True)


class MsvcLinker(BaseCompiler):
  ''' Interface for the MSVC linker. '''

  name = 'msvc:link'

  def __init__(self, program='link', **kwargs):
    super().__init__(program=program, **kwargs)

  def link(self, output, inputs, output_type='bin', frameworks=(),
      target_name=None, meta=None, **kwargs):
    '''
    Supported options:

      * keep_suffix
      * libpath
      * libs
      * msvc_libs
      * external_libs
      * msvc_external_libs
      * debug
      * description
      * program
      * additional_flags
      * msvc_additional_flags
      * msvc_link_additional_flags

    Target meta variables:

      * link_output -- The output filename of the link operation.
    '''

    builder = self.builder(inputs, frameworks, kwargs, name=target_name, meta=meta)

    if output_type not in ('bin', 'dll'):
      raise ValueError('unsupported output_type: {0}'.format(kind))
    keep_suffix = builder.get('keep_suffix', False)
    do_suffix = None if keep_suffix else getattr(platform, output_type)
    output = gen_output(output, suffix=do_suffix)

    libpath = builder.merge('libpath')
    libs = builder.merge('libs')
    libs += builder.merge('msvc_libs')
    external_libs = builder.merge('external_libs')
    external_libs += builder.merge('msvc_external_libs')
    debug = builder.get('debug', False)
    builder.target['description'] = builder.get('description', 'MSVC Link {0!r} ($out)'.format(output_type))

    command = [builder['program'], '/nologo', '$in', '/OUT:$out']
    command += ['/debug'] if debug else []
    command += ['/DLL'] if output_type == 'dll' else []
    command += ['/LIBPATH:{0}'.format(x) for x in libpath]
    command += [x + '.lib' for x in libs]
    command += external_libs
    command += builder.merge('additional_flags')
    command += builder.merge('msvc_additional_flags')
    command += builder.merge('msvc_link_additional_flags')

    builder.meta['link_output'] = output
    return builder.create_target(command, outputs=[output], implicit_deps=external_libs)


class MsvcAr(BaseCompiler):
  ''' Interface for the MSVC lib tool. '''

  name = 'msvc:lib'

  def __init__(self, program='lib', **kwargs):
    super().__init__(program=program, **kwargs)

  def staticlib(self, output, inputs, export=(), frameworks=(),
      target_name=None, meta=None, **kwargs):
    '''
    Supported options:

      * program
      * additional_flags
      * msvc_additional_flags
      * msvc_staticlib_additional_flags
      * description

    Target meta variables:

      * staticlib_output -- The output filename of the library operation.
    '''

    builder = self.builder(inputs, frameworks, kwargs, name=target_name, meta=meta)
    output = gen_output(output, suffix=platform.lib)

    command = [builder['program'], '/nologo']
    command += ['/export:' + x for x in export]
    command += builder.merge('additional_flags')
    command += builder.merge('msvc_additional_flags')
    command += builder.merge('msvc_staticlib_additional_flags')
    command += ['$in', '/OUT:$out']

    builder.target['description'] = builder.get('description', 'MSVC lib ($out)')
    builder.meta['staticlib_output'] = output
    return builder.create_target(command, outputs=[output])


Compiler = MsvcCompiler
Linker = MsvcLinker
Archiver = MsvcAr

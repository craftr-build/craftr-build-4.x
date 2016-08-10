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
'''
.. autofunction:: detect
.. autofunction:: get_vs_install_dir
.. autofunction:: get_vs_environment
.. autoclass:: MsvcCompiler
  :members:
  :undoc-members:
.. autoclass:: MsvcLinker
  :members:
  :undoc-members:
.. autoclass:: MsvcAr
  :members:
  :undoc-members:
.. autoclass:: MsvcSuite
  :members:
  :undoc-members:
'''

__all__ = ['detect', 'get_vs_install_dir', 'get_vs_environment',
  'MsvcCompiler', 'MsvcLinker', 'MsvcAr', 'MsvcSuite',
  'Compiler', 'Linker', 'Archiver']
__options__.add('rtti', bool, default=True)

from craftr import *
from craftr.ext.compiler import *
from craftr.ext import platform
from functools import lru_cache
import json, os, re, tempfile, sys


@lru_cache()
def detect(program):
  """
  Detects the version of the MSVC compiler from the specified
  *program* name and returns a dictionary with information that can
  be passed to the constructor of `MsvcCompiler` or raises
  `ToolDetectionError`.

  This function also supports detecting the Clang-CL compiler.

  :param program: The name of the program to execute and check.
  :return: :class:`dict` of

    * name (either ``'msvc'`` or ``'clang-cl'``)
    * version
    * version_str
    * target
    * thread_model
    * msvc_deps_prefix

  :raise OSError: If *program* can not be executed (eg. if it does not exist).
  :raise ToolDetectionError: If *program* is not GCC or GCC++.
  """

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
        if 'C1083' in line:  # C1083: can not open include file
          msg = 'MSVC can not compile a simple C program.\n  Program: {}\n  Output:\n\n{}'
          raise ToolDetectionError(msg.format(program, output))
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


@lru_cache()
def get_vs_environment(versions=None, prefer_newest=True, arch=None):
  """
  Returns the path to the newest installed version of Visual Studio.
  This is determined by reading the environment variables
  ``VS***COMNTOOLS``.

  If "versions" is specified, it must be a list of three-digit version
  numbers like ``100`` for Visual Studio 2010, ``110`` for 2012,
  ``120`` for 2013, ``140`` for 2015, etc.

  :param versions: Optionally, a list of acceptable Visual Studio
    version numbers that will be considered. If specified, the first
    detected installation will be used.
  :param prefer_newest: True if the newest version should be preferred.
  :return: tuple of (version, install_dir)
  :raise ToolDetectionError: If no Visual Studio insallation
    could be found.

  .. note::

    The option ``VSVERSIONS`` can be used to override the
    "versions" parameter if no explicit value is specified.

    The option ``VSARCH`` can be used to specify the default
    value for "arch" if no explicit value is specified.
  """

  if not versions:
    versions = [x for x in options.get('VSVERSIONS', '').split(',') if x]

  for v in versions:
    if len(v) != 3 or not all(c.isdigit() for c in v):
      raise ValueError('not a valid VS version: {0!r}'.format(v))

  if versions:
    choices = ['VS{0}COMNTOOLS'.format(x) for x in versions]
  else:
    choices = []
    for key, value in environ.items():
      if key.startswith('VS') and key.endswith('COMNTOOLS'):
        choices.append(key)
    choices.sort(reverse=prefer_newest)
  if not choices:
    raise ToolDetectionError('Visual Studio installation path could not be detected.')

  paths = []
  last_error = None
  for vsvar in choices:
    vsversion = vsvar[2:5]; assert(all(c.isdigit() for c in vsversion))
    vspath = environ.get(vsvar, '').rstrip('\\')
    if vspath:
      vspath = path.join(path.dirname(path.dirname(vspath)), 'VC')
      if not os.path.isdir(vspath):
        continue
      try:
        return _get_vs_environment(vspath, vsversion, arch)
      except ToolDetectionError as exc:
        last_error = exc

  if last_error:
    raise last_error

@lru_cache()
def _get_vs_environment(install_dir, vsversion, arch=None):
  parch = environ.get('PROCESSOR_ARCHITEW6432')
  if not parch:
    parch = environ.get('PROCESSOR_ARCHITECTURE', 'x86')
  parch = parch.lower()
  assert parch in ('x86', 'amd64', 'ia64')

  if arch is None:
    arch = options.get('VSARCH', parch)

  # Adjust the architecture if the host system is incompatible
  # (i.e. select the correct cross compiler).
  if parch in ('x86', 'amd64') and not arch.startswith(parch):
    arch = parch + '_' + arch

  if arch == 'x86':
    toolsdir = basedir = path.join(install_dir, 'bin')
    batch = path.join(toolsdir, 'vcvars32.bat')
  else:
    toolsdir = path.join(install_dir, 'bin', arch)
    basedir = path.join(install_dir, 'bin', parch)
    if arch == 'amd64':
      batch = path.join(toolsdir, 'vcvars64.bat')
    else:
      batch = path.join(toolsdir, 'vcvars' + arch + '.bat')

  # Run the batch file and print the environment.
  cmd = [batch, shell.safe('&&'), sys.executable,
    '-c', 'import os, json; print(json.dumps(dict(os.environ)))']
  try:
    out = shell.pipe(cmd, shell=True).output
  except OSError as exc:
    raise ToolDetectionError('Visual Studio Environment could not be detected: {}'.format(exc)) from exc
  env = json.loads(out)

  return {'basedir': basedir, 'toolsdir': toolsdir, 'env': env,
    'arch': arch, 'version': vsversion}


class MsvcCompiler(BaseCompiler):
  """
  Interface for the MSVC compiler.

  :param program: The name of the MSVC compiler program. If not specified,
    ``cl`` will be tested, otherwise :meth:`get_vs_install_dir` will
    be used.
  :param language: The language name to compile for. Must be ``c``,
    ``c++`` or ``asm``.
  :param desc: The description returned by :func:`detect`. If not
    specified, :func:`detect` will be called by the constructor.
  :param kwargs: Additional arguments that will be taken into account
    as a :class:`Framework` to :meth:`compile`.
  """

  name = 'msvc'

  def __init__(self, program='cl', language='c', desc=None, **kwargs):
    super().__init__(program=program, language=language, **kwargs)
    if language not in ('c', 'c++', 'asm'):
      raise ValueError('unsupported language: {0}'.format(language))
    if not desc:
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

      * language
      * include (``/I``) [list of str]
      * defines (``/D``) [list of str]
      * forced_include (``/FI``) [list of str]
      * debug (``/Od /Zi /RTC1 /FC /Fd /FS``) [``True, False``]
      * warn (``/W4, /w``) [``'all', 'none', None``]
      * optimize (``/Od, /O1, /O2, /Os``) [``'speed', 'size', 'debug', 'none', None]``
      * exceptions (``/EHsc``) [``True, False, None``]
      * rtti (``/GR[-]``) [``True, False, None``]
      * autodeps (``/showIncludes``)
      * description
      * msvc_runtime_library (``/MT, /MTd, /MD, /MDd``) [``'static', 'dynamic', None``]
      * msvc_disable_warnings (``/wd``) [list of int/str]
      * program
      * additional_flags
      * msvc_additional_flags
      * msvc_compile_additional_flags
      * msvc_remove_flags
      * msvc_compile_remove_flags
      * msvc_use_default_defines

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

    language = builder['language']
    debug = builder.get('debug', False)
    builder.target['description'] = builder.get('description', '{0} Compile Object ($out)'.format(self.name))

    if language not in ('c', 'c++', 'asm'):
      raise ValueError('invalid language: {0!r}'.format(language))

    defines = builder.merge('defines')
    if builder.get('msvc_use_default_defines', True):
      defines += ['WIN32', '_WIN32']

    command = [builder['program'], '/nologo', '/c', '$in', '/Fo$out']
    command += ['/wd' + str(x) for x in builder.merge('msvc_disable_warnings')]
    command += ['/we' + str(x) for x in builder.merge('msvc_warnings_as_errors')]
    command += ['/I' + x for x in builder.merge('include')]
    command += ['/D' + x for x in defines]
    command += ['/FI' + x for x in builder.merge('forced_include')]
    if debug:
      command += ['/Od', '/Zi', '/RTC1', '/FC', '/Fd$out.pdb']
      if not self.version or self.version >= 'v18':
        # Enable parallel writes to .pdb files. We also assume that this
        # option is necessary by default.
        command += ['/FS']

    exceptions = builder.get('exceptions', None)
    if exceptions:
      if language != 'c++':
        builder.invalid_option('exception', True, cause='not supported in {0!r}'.format(language))
      command += ['/EHsc']
    elif exceptions is None and language == 'c++':
      # Enable exceptions by default.
      command += ['/EHsc']

    rtti = builder.get('rtti', None)
    if rtti is not None:
      command += ['/GR'] if rtti else ['/GR-']

    warn = builder.get('warn', 'all')
    if warn == 'all':
      # /Wall really shows too many warnings, /W4 is pretty good.
      command += ['/W4']
    elif warn == 'none':
      command += ['/w']
    elif warn is None:
      pass
    else:
      builder.invalid_option('warn')

    optimize = builder.get('optimize', None)
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

    msvc_runtime_library = builder.get('msvc_runtime_library', 'dynamic')
    if msvc_runtime_library == 'dynamic':
      command += ['/MTd' if debug else '/MT']
    elif msvc_runtime_library == 'static':
      command += ['/MDd' if debug else '/MD']
    elif msvc_runtime_library is not None:
      raise ValueError('invalid msvc_runtime_library: {0!r}'.format(msvc_runtime_library))

    autodeps = builder.get('autodeps', True)
    if autodeps:
      builder.target['deps'] = 'msvc'
      builder.target['msvc_deps_prefix'] = self.deps_prefix
      command += ['/showIncludes']
    command += builder.merge('additional_flags')
    command += builder.merge('msvc_additional_flags')
    command += builder.merge('msvc_compile_additional_flags')

    remove_flags(command, builder.merge('msvc_remove_flags'), builder)
    remove_flags(command, builder.merge('msvc_compile_remove_flags'), builder)
    return builder.create_target(command, outputs=objects, foreach=True)


class MsvcLinker(BaseCompiler):
  ''' Interface for the MSVC linker. '''

  name = 'msvc:link'

  def __init__(self, program='link', desc=None, **kwargs):
    if desc is None:
      raise TypeError('MsvcLinker requires description of MsvcCompiler')
    super().__init__(program=program, **kwargs)
    self.desc = desc

  def link(self, output, inputs, frameworks=(),
      target_name=None, meta=None, **kwargs):
    '''
    Supported options:

      * output_type
      * keep_suffix (overrides force_suffix)
      * force_suffix
      * libpath
      * libs
      * msvc_libs
      * win32_libs
      * win64_libs
      * external_libs
      * msvc_external_libs
      * debug
      * description
      * program
      * additional_flags
      * msvc_additional_flags
      * msvc_link_additional_flags
      * msvc_remove_flags
      * msvc_link_remove_flags

    Target meta variables:

      * link_output -- The output filename of the link operation.
      * link_target -- The filename that can be specified to the linker.
        This is necessary because on Windows you pass in a separately
        created ``.lib`` file instead of the ``.dll`` output file.
    '''

    builder = self.builder(inputs, frameworks, kwargs, name=target_name, meta=meta)

    output_type = builder.get('output_type', 'bin')
    if output_type not in ('bin', 'dll'):
      raise ValueError('unsupported output_type: {0}'.format(kind))

    # Generate the output filename, keeping the suffix or forcing
    # a specific suffix based on the respective options.
    keep_suffix = builder.get('keep_suffix', False)
    suffix = builder.get('force_suffix', None)
    if keep_suffix:
      suffix = None
    elif not suffix:
      suffix = getattr(platform, output_type)
    output = gen_output(output, suffix=suffix)

    libpath = builder.merge('libpath')
    libs = builder.merge('libs')
    libs += builder.merge('msvc_libs')
    if self.desc['target'] == 'x86':
      libs += builder.merge('win32_libs')
    else:
      libs += builder.merge('win64_libs')
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

    remove_flags(command, builder.merge('msvc_remove_flags'), builder)
    remove_flags(command, builder.merge('msvc_link_remove_flags'), builder)

    builder.meta['link_output'] = output
    if output_type == 'dll':
      builder.meta['link_target'] = path.setsuffix(output, '.lib')
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


class MsvcSuite(object):
  """
  Represents an MSVC installation and its meta information.
  """

  def __init__(self, vsversions=None, vsarch=None):
    data = get_vs_environment(vsversions)
    self.basedir = data['basedir']
    self.toolsdir = data['toolsdir']
    self.env = data['env']
    self.version = data['version']

    # TODO: This is a dirty hack to make sure the Visual Studio
    #       compiler can be run until craftr-build/craftr#120 is
    #       implemented.
    utils.prepend_path(self.basedir)
    utils.prepend_path(self.toolsdir)

    cl = path.join(self.toolsdir, 'cl.exe')
    link = path.join(self.toolsdir, 'link.exe')
    lib = path.join(self.toolsdir, 'lib.exe')
    with utils.override_environ(self.env):
      self.desc = detect(cl)

    self.include = tuple(filter(bool, self.env['INCLUDE'].split(os.pathsep)))
    self.libpath = tuple(filter(bool, self.env['LIBPATH'].split(os.pathsep)))
    self.lib = tuple(filter(bool, self.env['LIB'].split(os.pathsep)))

    self.cc = MsvcCompiler(cl, 'c', desc=self.desc, include=self.include, libpath=self.libpath)
    self.cxx = MsvcCompiler(cl, 'c++', desc=self.desc, include=self.include, libpath=self.libpath)
    self.asm = MsvcCompiler(cl, 'asm', desc=self.desc, include=self.include, libpath=self.libpath)
    self.ld = MsvcLinker(link, desc=self.desc, libpath=self.lib)
    self.ar = MsvcAr(lib)

    info('Detected: Microsoft Visual Studio Compiler v{0}:{1}'.format(self.version, data['arch']))


Compiler = MsvcCompiler
Linker = MsvcLinker
Archiver = MsvcAr

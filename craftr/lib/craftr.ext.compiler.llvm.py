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

__all__ = ['detect', 'LlvmCompiler', 'Compiler', 'Linker']

from craftr import *
from craftr.ext import platform
from craftr.ext.compiler import *

from functools import partial
import re


_e_llvm_version = r'^.*(clang|llvm)\s+version\s+([\d\.\-]+).*$'
_e_llvm_target = r'Target:\s*([\w\-\._]+)'
_e_llvm_thread = r'Thread\s+model:\s*([\w\-\._]+)'


@memoize_tool
def detect(program):
  ''' Assuming *program* points to Clang or Clang++, this function
  determines meta information about it. The returned dictionary contains
  the following keys:

  :param version:
  :param version_str:
  :param name:
  :param target:
  :param thread_model:
  :param cpp_stdlib: (only present for Clang++)

  :raise OSError: If *program* can not be executed (eg. if it does not exist).
  :raise ToolDetectionError: If *program* is not Clang or Clang++. '''

  output = shell.pipe([program, '-v']).output
  version = utils.gre_search(_e_llvm_version, output, re.I | re.M)
  target = utils.gre_search(_e_llvm_target, output, re.I)[1]
  thread_model = utils.gre_search(_e_llvm_thread, output, re.I)[1]
  del output

  if not all(version):
    raise ToolDetectionError('could not determine LLVM version')

  result = {
    'version': version[2],
    'version_str': version[0].strip(),
    'name': version[1].lower(),
    'target': target,
    'thread_model': thread_model,
  }

  # Check for a C++ compiler.
  if program[-2:] == '++':
    stdlib = detect_cpp_stdlib(program)
    if stdlib:
      result['cpp_stdlib'] = stdlib

  return result


def detect_cpp_stdlib(program):
  ''' Performs a test compilation of a C++ file with *program*
  and tries to determine the C++ stdlib that is required for
  linking. '''

  # Just create a temporary C++ file to be able to read the link
  # flags that would be invoked.
  with utils.tempfile(suffix='.cpp') as fp:
    fp.close()
    output = shell.pipe([program, '-v', fp.name]).output.split('\n')
    # Check for a line that looks like a linker command.
    for line in output:
      try:
        parts = shell.split(line)
      except ValueError:
        continue
      if not line:
        continue
      program = parts[0].lower().split(path.sep)
      if 'ld' in program or 'collect2' in program:
        # Looking good. Is it using -lc++ or -lstdc++?
        if '-lc++' in parts:
          return 'c++'
        elif '-lstdc++' in parts:
          return 'stdc++'
        else:
          warn('C++ stdlib could not be detected.')
  return None


class LlvmCompiler(BaseCompiler):
  ''' Interface for the LLVM compiler. '''

  name = 'LLVM'
  _supported_compilers = ('gcc', 'clang', 'llvm')

  def __init__(self, program, language, desc=None, **kwargs):
    super().__init__(program=program, language=language, **kwargs)
    if not desc:
      desc = detect(program)
    self.desc = desc
    self.version = desc['version']
    self.name = desc['name']
    assert self.name in ('gcc', 'clang', 'llvm'), self.name

  def compile(self, sources, frameworks=(), target_name=None,  **kwargs):
    '''
    :param sources: A list of input source files.
    :param frameworks: List of :class:`Framework` objects.
    :param target_name: Override target name.

    Supported framework options:

    :param include: Additional include directories.
    :param defines: Preprocessor definitions.
    :param language: Override compilation language. Choices are
      ``'c'``, ``'cpp'``, ``'asm'``
    :param debug: True ot disable optimizations and enable debugging symbols.
    :param std: Set the C/C++ standard (``--std`` argument)
    :param pedantic: Enable the ``--pedantic`` flag
    :param pic: Enable position independent code.
    :param warn: Warning level. Choices are ``'all'``, ``'none'`` and
      :const:`None` (latter is different in that it adds no warning related
      compiler flag at all).
    :param optimize: Optimization level. Choices are ``'debug'``, ``'speed'``,
      ``'size'``, ``'none'`` and :const:`None`
    :param autodeps: True if automatic dependencies should be enabled
      (for recompiles when only headers change). Default is True.
    :param description: Target description (shown during Ninja build).
    :param osx_fwpath: Additional search path for OSX frameworks.
    :param osx_frameworks: OSX frameworks to take into account.
    :param program: Override the compiler command.
    :param additional_flags: Additional flags for the compiler command-
    :param gcc_additional_flags: Additional flags (GCC only).
    :param gcc_compile_additional_flags: Additional flags (GCC only).
    :param llvm_additional_flags: Additional flags (LLVM only).
    :param llvm_compile_additional_flags: Additional flags (LLVM only).
    '''

    builder = self.builder(sources, frameworks, kwargs, name=target_name)
    objects = gen_objects(builder.inputs, suffix=platform.obj)
    fw = builder.add_framework(builder.name)

    include = utils.unique(builder.merge('include'))
    defines = utils.unique(builder.merge('defines'))
    language = builder['language']
    debug = builder.get('debug', False)
    std = builder.get('std')
    pedantic = builder.get('pedantic', False)
    pic = builder.get('pic', False)
    warn = builder.get('warn', 'all')
    optimize = builder.get('optimize', None)
    autodeps = builder.get('autodeps', True)
    description = builder.get('description', None)
    if not description:
      description = '{0} compile $out'.format(self.name)

    if platform.name == 'Darwin':
      osx_fwpath = builder.merge('osx_fwpath')
      osx_frameworks = builder.merge('osx_frameworks')
    else:
      osx_fwpath = []
      osx_frameworks = []

    if language not in (None, 'c', 'c++', 'asm'):
      raise ValueError('invalid language: {0}'.format(language))

    stdlib = None
    if language == 'c++':
      stdlib = builder.get('cpp_stdlib', None)
      if not stdlib:
        stdlib = self.desc.get('cpp_stdlib', 'stdc++')
      fw['libs'] = [stdlib]

    command = [builder['program']]
    if language == 'asm':
      command += ['-x', 'assembler']
    elif language:
      command += ['-x', language]
    command += ['-c', '$in', '-o', '$out']
    command += ['-g'] if debug else []
    command += ['-std=' + std] if std else []
    if self.name in ('clang', 'llvm'):
      command += ['-stdlib=lib' + stdlib] if stdlib else []
    command += ['-pedantic'] if pedantic else []
    command += ['-I' + x for x in include]
    command += ['-D' + x for x in defines]
    command += ['-fPIC'] if pic else []
    command += ['-F' + x for x in osx_fwpath]
    command += utils.flatten(['-framework', x] for x in osx_frameworks)

    if warn == 'all':
      command += ['-Wall']
    elif warn == 'none':
      command += ['-w']
    elif warn is None:
      pass
    else:
      builder.invalid_option('warn')

    if debug:
      if optimize and optimize != 'debug':
        builder.invalid_option('optimize', cause='no optimize with debug enabled')
    elif optimize == 'speed':
      command += ['-O4']
    elif optimize == 'size':
      commandm += ['-Os']
    elif optimize in ('debug', 'none', None):
      command += ['-O0']
    else:
      builder.invalid_option('optimize')

    if autodeps:
      builder.target['depfile'] = '$out.d'
      builder.target['deps'] = 'gcc'
      command += ['-MD', '-MP', '-MF', '$depfile']

    command += builder.merge('additional_flags')
    if self.name in ('clang', 'llvm'):
      command += builder.merge('llvm_additional_flags')
      command += builder.merge('llvm_compile_additional_flags')
    elif self.name == 'gcc':
      command += builder.merge('gcc_additional_flags')
      command += builder.merge('gcc_compile_additional_flags')
    else:
      assert False, self.name

    if session.buildtype == 'external':
      if language == 'c':
        command += shell.split(options.get('CFLAGS', ''))
      elif language == 'c++':
        command += shell.split(options.get('CPPFLAGS', ''))
      elif language == 'asm':
        command += shell.split(options.get('ASMFLAGS', ''))

    return builder.create_target(command, outputs=objects, foreach=True,
      description=description)

  def link(self, output, inputs, output_type='bin', frameworks=(),
      target_name=None, **kwargs):
    '''

    :param output: The name of the output file. The platform-dependent
      appropriate suffix is automatically appended unless *keep_suffix*
      is True.
    :param inputs: A list of input files/targets.
    :param output_type: The output type. Can be ``'bin'`` or ``'dll'``
    :param frameworks: List of additional :class:`Framework` objects.
      Note that the frameworks of :class:`Target` objects listed in
      *inputs* are taken into account automatically.
    :param target_name: Override target name.

    Supported framework options:

    :param keep_suffix: Do not replace the suffix of the specified *output* files.
    :param debug: True to enable debug symbols and disable optimization.
    :param libs: Additional library names to link with.
    :param gcc_libs: Additional library names to link with (GCC only).
    :param llvm_libs: Additional library names to link with (LLVM only).
    :param linker_args: Additional linker aguments.
    :param gcc_linker_args: Additional linker aguments (GCC only).
    :param llvm_linker_args: Additional linker aguments (LLVM only).
    :param linker_script: Linker script input file.
    :param libpath: Additional search directory to search for libraries.
    :param external_libs: Absolute paths of additional libraries to link with.
    :param osx_fwpath: Additional search path for frameworks (OSX only).
    :param osx_frameworks: Frameworks to link with (OSX only).
    :param description: Target description (displayed during Ninja build).
    :param program: Override the linker program to incoke.
    :param additional_flags: Additional flags for the linker.
    :param gcc_additional_flags: Additional flags for the linker (GCC only).
    :param llvm_additional_flags: Additional flags for the linker (LLVM only).
    :param gcc_link_additional_flags: Additional flags for the linker (GCC only).
    :param llvm_link_additional_flags: Additional flags for the linker (LLVM only).

    :attr:`Target.meta` variables:

    :param link_output: The output filename of the link operation.
    '''

    builder = self.builder(inputs, frameworks, kwargs, name=target_name)

    if output_type not in ('bin', 'dll'):
      raise ValueError('invalid output_type: {0!r}'.format(output_type))
    keep_suffix = builder.get('keep_suffix', False)
    do_suffix = None if keep_suffix else getattr(platform, output_type)
    output = gen_output(output, suffix=do_suffix)
    implicit_deps = []

    debug = builder.get('debug', False)
    libs = builder.merge('libs')
    # Clang is based on GCC libraries, so always use the gcc_libs option.
    libs += builder.merge('gcc_libs')
    if self.name in ('clang', 'llvm'):
      # We also use this class for GCC in which case the llvm_libs
      # option should not be handled!
      libs += builder.merge('llvm_libs')

    linker_args = builder.merge('linker_args')
    linker_args += builder.merge('gcc_linker_args')
    if self.name in ('clang', 'llvm'):
      linker_args += builder.merge('llvm_linker_args')

    linker_script = builder.get('linker_script', None)
    if linker_script:
      implicit_deps.append(linker_script)
      linker_args += ['-T', linker_script]

    libpath = builder.merge('libpath')
    external_libs = builder.merge('external_libs')
    implicit_deps += external_libs

    if platform.name == 'mac':
      osx_fwpath = builder.merge('osx_fwpath')
      osx_frameworks = builder.merge('osx_frameworks')
    else:
      osx_fwpath = []
      osx_frameworks = []

    description = builder.get('description', None)
    if not description:
      description = '{0} Link $out'.format(self.name)

    command = [builder['program'], '$in']
    command += ['-g'] if debug else []
    command += ['-l' + x for x in utils.unique(libs)]
    command += ['-L' + x for x in utils.unique(libpath)]
    command += utils.unique(external_libs)
    command += ['-shared'] if output_type == 'dll' else []
    command += ['-F' + x for x in osx_fwpath]
    command += utils.flatten(['-framework', x] for x in osx_frameworks)
    if linker_args:
      command += ['-Wl,' + ','.join(linker_args)]
    command += builder.merge('additional_flags')
    if self.name in ('clang', 'llvm'):
      command += builder.merge('llvm_additional_flags')
      command += builder.merge('llvm_link_additional_flags')
    elif self.name == 'gcc':
      command += builder.merge('gcc_additional_flags')
      command += builder.merge('gcc_link_additional_flags')
    else:
      assert False, self.name
    command += ['-o', '$out']

    if session.buildtype == 'external':
      command = []
      flags = shell.split(options.get('LDFLAGS', '').strip())
      wlflags = sum(1 for s in flags if s.startswith('-Wl,'))
      if wlflags > 0 and wlflags != len(flags):
        error('LDFLAGS must be either in -Wl, or raw arguments format. Got:\n::  LDFLAGS=' + options.get('LDFLAGS', ''))
      if flags and wlflags == 0:
        # The flags are not in -Wl, format, so we convert them to
        # a single -Wl, argument.
        flags = ['-Wl,' + ','.join(flags)]

      command += flags
      command += shell.split(options.get('LDLIBS', ''))

    builder.meta['link_output'] = output
    return builder.create_target(command, outputs=[output],
      implicit_deps=implicit_deps, description=description)


Compiler = LlvmCompiler
Linker = partial(LlvmCompiler, language='c')

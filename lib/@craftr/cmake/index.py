"""
Allows you to include CMake projects in your build pipeline.
"""

import collections
import os
import re
import string
import craftr, {path} from 'craftr'

ConfigResult = collections.namedtuple('ConfigResult', 'output directory')


def configure_file(input, output=None, environ={}, inherit_environ=True):
  """
  Renders the CMake configuration file using the specified environment
  and additionally the current process environment (optional).

  If the #output parameter is omitted, an output filename in a
  special ``include/`` directory will be generated from the *input*
  filename. The ``.in`` suffix from #input will be removed if it
  exists.

  :param input: Absolute path to the CMake config file.
  :param output: Name of the output file. Will be automatically
    generated if omitted.
  :param environ: A dictionary containing the variables for
    rendering the CMake configuration file. Non-existing
    variables are considered undefined.
  :param inherit_environ: If True, the environment variables of the
    Craftr process are additionally taken into account.
  :return: A :class:`ConfigResult` object.
  """

  input = craftr.localpath(input)

  if not output:
    output = craftr.buildlocal('include', path.base(input))
    if output.endswith('.in'):
      output = output[:-3]
    elif output.endswith('.cmake'):
      output = output[:-6]

  if inherit_environ:
    new_env = os.environ.copy()
    new_env.update(environ)
    environ = new_env
    del new_env

  output_dir = path.dir(output)
  path.makedirs(output_dir)

  def replace_var(match):
    return environ.get(match.group(1), '')

  with open(input) as src:
    with open(output, 'w') as dst:
      for line_num, line in enumerate(src):
        match = re.match('\s*#cmakedefine(01)?\s+(\w+)\s*(.*)', line)
        if match:
          is01, var, value = match.groups()
          if is01 and value:
            raise ValueError("invalid configuration file: {!r}\n"
              "line {}: #cmakedefine01 does not expect a value part".format(input, line_num))
          if is01:
            if environ.get(var):
              line = '#define {} 1\n'.format(var)
            else:
              line = '#define {} 0\n'.format(var)
          else:
            if environ.get(var):
              line = '#define {} {}\n'.format(var, value)
            else:
              line = '/* #undef {} */\n'.format(var)

        line = re.sub('@([A-z_0-9]+)@', replace_var, line)

        # Replace variable references with $X or ${X}
        def replace(match):
          value = environ.get(match.group(3), None)
          if value:
            return str(value)
          return ''
        line = string.Template.pattern.sub(replace, line)

        dst.write(line)

  return ConfigResult(output, output_dir)


# ============================================================================
# Prototype from a previous Craftr version to build CMake projects from
# Craftr. This is incomplete and should not be used, it exists purely in order
# to be polished in the future.
# ============================================================================

import cxx from '@craftr/cxx'
import msvc from '@craftr/msvc'

class Generator:

  name = None

  def get_output_files(self, target):
    raise NotImplementedError

  def build_action(self, target, gen_action):
    raise NotImplementedError


class MsvcGenerator:

  def __init__(self, toolkit=None):
    if not toolkit:
      toolkit = msvc.MsvcToolkit.get()
    version = toolkit.version // 10
    year = {15: 2017, 14: 2015, 12: 2013, 11: 2012, 10: 2010, 9: 2008,
            8: 2005}[version]
    arch = 'Win64' if toolkit.cl_info.target == 'x64' else None  # TODO: IA64/ARM??
    self.name = 'Visual Studio {} {}'.format(version, year, arch)
    if arch:
      self.name += ' ' + arch
    self.toolkit = toolkit

  def get_output_files(self, target):
    return [path.join(target.data.build_dir, target.data.cmake_project_name + '.sln')]

  def build_action(self, target, gen_action):
    return craftr.actions.System.new(
      target,
      name = 'cmake_build',
      commands = [['msbuild', path.abs(self.get_output_files(target)[0])]],
      deps = [gen_action],
      cwd = target.data.build_dir,
      environ = self.toolkit.environ
    )


class UnixMakeGenerator:

  name = 'Unix Makefiles'

  # TODO


class CmakeTarget(object):  #craftr.target.TargetData

  def __init__(self, project_dir, build_dir=None, lib_dir=None, generator=None,
               options=None, shared_options=None, static_options=None,
               build_type=None):
    if not generator:
      if os.name == 'nt':
        generator = MsvcGenerator(msvc.MsvcToolkit.get())
      else:
        generator = UnixMakeGenerator()
    self.project_dir = project_dir
    self.cmakelists_filename = path.join(self.project_dir, 'CMakeLists.txt')
    self.build_dir = build_dir
    self.lib_dir = lib_dir
    self.build_type = build_type
    self.generator = generator
    self.options = options or []
    self.shared_options = shared_options
    self.static_options = static_options
    self.preferred_linkage = 'any'

  @property
  def cmakelists_source(self):
    if not hasattr(self, '_cmakelists_source'):
      with open(self.cmakelists_filename) as fp:
        self._cmakelists_source = fp.read()
    return self._cmakelists_source

  @property
  def cmake_project_name(self):
    if not hasattr(self, '_cmake_project_name'):
      for line in self.cmakelists_source.split('\n'):
        line = line.strip()
        m = re.match('project\s*\(\s*([^\)\n]+)\s*\)', line)
        if m: break
      else:
        raise ValueError('could not determine CMake Project Name from "{}"'.format(self.cmakelists_filename))
      self._cmake_project_name = m.group(1)
    return self._cmake_project_name

  def add_library(self, name, library_name=None, **kwargs):
    def unwrapper(target):
      nonlocal library_name
      assert self.target.is_completed(), 'CMake target is not completed'
      assert self.preferred_linkage in ('static', 'shared')

      if not library_name:
        library_name = name
        if self.preferred_linkage == 'static':
          library_name += '-s-d'

      shared_libs = []
      static_libs = []
      if os.name == 'nt':
        library_name += '.lib'
      elif self.preferred_linkage == 'static':
        library_name = path.addprefix(library_name, 'lib') + '.a'
      elif self.preferred_linkage == 'shared':
        library_name = path.addprefix(library_name, 'lib') + '.so'
      library_name = path.join(self.lib_dir, library_name)
      if self.preferred_linkage == 'static':
        static_libs.append(library_name)
      elif self.preferred_linkage == 'shared':
        shared_libs.append(library_name)
      return cxx.CxxPrebuilt(
        shared_libs = shared_libs,
        static_libs = static_libs,
        **kwargs
      )
    self.target.add_trait(craftr.ProxyTarget(unwrapper))

  def complete(self, target):
    target.console = True
    if not self.build_dir:
      self.build_dir = path.join(target.cell.builddir, path.base(self.project_dir))
    else:
      self.build_dir = path.canonical(self.build_dir)
    if not self.build_type:
      self.build_type = 'Debug'# 'Debug' if cxx.infer_debug(target) else 'Release'
    if not self.lib_dir:
      self.lib_dir = 'lib/{BUILD_TYPE}'

    # TODO: Is this only for SFML or does CMake always output into the 'Debug'
    #       directory even for a Release build?
    self.lib_dir = path.canonical(self.lib_dir.format(BUILD_TYPE='Debug'), self.build_dir)
    self.options.append('CMAKE_BUILD_TYPE=' + self.build_type)

    if self.preferred_linkage == 'any':
      self.preferred_linkage = cxx.infer_linkage(target)
    assert self.preferred_linkage in ('static', 'shared'), self.preferred_linkage
    if self.preferred_linkage == 'shared' and self.shared_options:
      self.options += self.shared_options
    elif self.preferred_linkage == 'static' and self.static_options:
      self.options += self.static_options

  def translate(self, target):
    command = ['cmake', self.project_dir]
    command += ['-D{}'.format(x) for x in self.options]
    command += ['-G', self.generator.name]
    gen_action = craftr.actions.System.new(
      target,
      name = 'cmake_gen',
      input_files = [self.cmakelists_filename],
      output_files = self.generator.get_output_files(target),
      commands = [command],
      cwd = self.build_dir
    )
    self.generator.build_action(target, gen_action)


#build = craftr.target_factory(CmakeTarget)

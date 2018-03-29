
from nr import path

import functools
import nr.named
import os
import re
import requests
import subprocess

import {context, options} from './build.craftr'
import craftr, {OS} from 'craftr.craftr'
import sh from '@craftr/craftr-build/utils/sh'
import nupkg from './tools/nupkg'

if OS.type == 'nt':
  import msvc from 'tools.msvc.craftr'
else:
  msvc = None

artifacts_dir = path.join(context.build_directory, 'csharp', 'nuget')


class CscInfo(nr.named.named):

  __annotations__ = [
    ('impl', str),
    ('program', list),
    ('environ', dict),
    ('version', str),
    ('netversion', str, 'net45')  # TODO: determine default netversion here
  ]

  def __repr__(self):
    return '<CscInfo impl={!r} program={!r} environ=... version={!r}>'\
      .format(self.impl, self.program, self.version)

  def is_mono(self):
    assert self.impl in ('net', 'mono'), self.impl
    return self.impl == 'mono'

  def exec_args(self, argv):
    if self.is_mono():
      return ['mono'] + argv
    return argv

  def get_nuget(self):
    """
    Checks if the `nuget` command-line program is available, and otherwise
    downloads it into the artifact directory.
    """

    local_nuget = path.join(artifacts_dir, 'nuget.exe')
    if not path.isfile(local_nuget):
      if sh.which('nuget') is not None:
        return ['nuget']
      print('[Downloading] NuGet ({})'.format(local_nuget))
      response = requests.get('https://dist.nuget.org/win-x86-commandline/latest/nuget.exe')
      response.raise_for_status()
      path.makedirs(artifacts_dir, exist_ok=True)
      with open(local_nuget, 'wb') as fp:
        for chunk in response.iter_content():
          fp.write(chunk)
      path.chmod(local_nuget, '+x')
    return self.exec_args([path.abs(local_nuget)])

  def get_merge_tool(self, out, primary, assemblies=()):
    """
    Checks if the `ILMerge` or `ILRepack` command-line program is available, and
    otherwise installs it using NuGet into the artifact directory.
    """

    tool = options.mergeTool
    if not tool:
      if self.is_mono():
        tool = 'ILRepack:2.0.13'
      else:
        tool = 'ILMerge:2.14.1208'

    tool_name, version = tool.partition(':')[::2]
    local_tool = path.join(artifacts_dir, tool_name + '.' + version, 'tools', tool_name + '.exe')
    command = None
    if not path.isfile(local_tool):
      if sh.which(tool_name) is not None:
        command = [tool_name]
      else:
        install_cmd = self.get_nuget() + ['install', tool_name, '-Version', version]
        print('[Installing] {}.{}'.format(tool_name, version))
        path.makedirs(artifacts_dir, exist_ok=True)
        subprocess.check_call(install_cmd, cwd=artifacts_dir)

    if not command:
      command = self.exec_args([path.abs(local_tool)])

    return command + ['/out:' + out] + [primary] + list(assemblies)

  @staticmethod
  @functools.lru_cache()
  def get():
    if options.impl not in ('net', 'mono'):
      raise ValueError('unsupported csharp.impl={!r}'.format(impl))

    program = options.csc
    is_mcs = path.rmvsuffix(program).lower().endswith('mcs')

    if options.impl == 'net':
      toolkit = msvc.MsvcToolkit.get()
      csc = CscInfo(options.impl, [program], toolkit.environ, toolkit.csc_version)
    else:
      environ = {}
      if OS.type == 'nt':
        # Also, just make sure that we can find some standard installation
        # of Mono.
        arch = options.monoArch
        monobin_x64 = path.join(os.getenv('ProgramFiles'), 'Mono', 'bin')
        monobin_x86 = path.join(os.getenv('ProgramFiles(x86)'), 'Mono', 'bin')
        if arch is None:
          if path.isdir(monobin_x64):
            monobin = monobin_x64
          else:
            monobin = monobin_x86
        elif arch == 'x64':
          monobin = monobin_x64
        elif arch == 'x86':
          monobin = monobin_x86
        else:
          raise ValueError('invalid value csharp.mono_arch={!r}'.format(arch))
        environ['PATH'] = monobin + path.pathsep + os.getenv('PATH')

        # On windows, the mono compiler is available as .bat file, thus we
        # need to run it through the shell.
        program = sh.shellify([program])
      else:
        program = [program]

      if is_mcs:
        with sh.override_environ(environ):
          version = subprocess.check_output(program + ['--version']).decode().strip()
        m = re.search('compiler\s+version\s+([\d\.]+)', version)
        if not m:
          raise ValueError('Mono compiler version could not be detected from:\n\n  ' + version)
        version = m.group(1)
      else:
        with sh.override_environ(environ):
          version = subprocess.check_output(program + ['/version']).decode().strip()

      csc = CscInfo(options.impl, program, environ, version)

    return csc


class CsharpTargetHandler(craftr.TargetHandler):

  def __init__(self, csc):
    self.csc = csc

  def init(self, context):
    props = context.target_properties
    props.add('csharp.srcs', craftr.StringList)
    props.add('csharp.type', craftr.String, 'exe')  # appcontainer, exe, library, module, winexe, winmdobj
    props.add('csharp.main', craftr.String)
    props.add('csharp.productName', craftr.String)
    props.add('csharp.compilerFlags', craftr.StringList)
    props.add('csharp.dynamicLibraries', craftr.StringList)
    props.add('csharp.packages', craftr.StringList)
    props.add('csharp.bundle', craftr.Bool, False)  # Allows you to enable bundling of assemblies.
    props.add('csharp.runArgsPrefix', craftr.StringList)
    props.add('csharp.runArgs', craftr.StringList)

    props = context.dependency_properties
    props.add('csharp.bundle', craftr.Bool, True)

  def translate_target(self, target):
    build_dir = path.join(context.build_directory, target.module.name)
    data = target.get_props('csharp.', as_object=True)

    # Install artifacts.
    data.compilerFlags = target.get_prop_join('csharp.compilerFlags')
    data.dynamicLibraries = target.get_prop_join('csharp.dynamicLibraries')
    data.dynamicLibraries += self.__install(data.packages)

    # Prepare information for compiling a product.
    if data.srcs:
      if data.type in ('appcontainerexe', 'exe', 'winexe'):
        suffix = '.exe'
      elif data.type == 'winmdobj':
        suffix = '.winmdobj'
      elif data.type == 'module':
        suffix = '.netmodule'
      elif data.type == 'library':
        suffix = '.dll'
      else:
        raise ValueError('invalid csharp.type: {!r}'.format(data.type))

      if not data.productName:
        data.productName = target.name + '-' + target.module.version
      data.productFilename = path.join(build_dir, data.productName + suffix)
      data.bundleFilename = None
      if data.bundle:
        data.bundleFilename = path.addtobase(data.productFilename, '-bundle')

    if data.srcs:
      bundleModules = []
      modules = []
      bundleReferences = list(data.dynamicLibraries)
      references = []
      for dep in target.transitive_dependencies():
        depData = dep.handler_data(self)
        for dep_target in dep.sources:
          files = dep_target.files_tagged(['out', 'csharp.module'])[1]
          if depData.bundle: bundleModules += files
          else: modules += files
          files = dep_target.files_tagged(['out', '!csharp.module', 'csharp.*'])[1]
          if depData.bundle: bundleReferences += files
          else: references += files

      # Action to compile the C# sources into the target product type.
      command = self.csc.program + ['-nologo', '-target:' + data.type]
      command += ['-out:$out']
      if data.main:
        command += ['-main:' + data.main]
      if modules or bundleModules:
        command.append('-addmodule:' + ';'.join(modules + bundleModules))
      if references or bundleReferences:
        command += ['-reference:' + x for x in (references + bundleReferences)]
      if data.compilerFlags:
        command += data.compilerFlags
      command += ['$in']
      action = target.add_action('csharp.compile', commands=[command],
        environ=self.csc.environ)
      build = action.add_buildset()
      build.files.add(data.srcs, ['in'])
      build.files.add(data.productFilename, ['out', 'csharp.' + data.type])

      # Action to run the product.
      command = list(data.runArgsPrefix or self.csc.exec_args([]))
      command += [data.productFilename]
      command += data.runArgs
      # TODO: Seems like there is no option or environment variable to
      #       allow the .NET runtime to find the assemblies in other directories?
      action = target.add_action('csharp.run', commands=[command], explicit=True,
        syncio=True, output=False)
      action.add_buildset()

    # Action to merge the generated references into one file.
    if data.bundleFilename and data.bundle:
      command = self.csc.get_merge_tool(out='$out', primary='$in',
        assemblies=references + bundleReferences)
      action = target.add_action('csharp.bundle', commands=[command])
      build = action.add_buildset()
      build.files.add(data.productFilename, ['in'])
      build.files.add(data.bundleFilename, ['out', 'csharp.' + data.type + 'Bundle'])

      # Action to run the product.
      command = list(data.runArgsPrefix or self.csc.exec_args([]))
      command += [data.bundleFilename]
      command += data.runArgs
      action = target.add_action('csharp.runBundle', commands=[command],
        explicit=True, syncio=True, output=False)
      action.add_buildset()

  def __install(self, packages):
    packages = [nupkg.Dependency.from_str(x) for x in packages]
    deps = set()
    result = []
    path.makedirs(artifacts_dir, exist_ok=True)
    for dep in packages:
      deps.add(dep)

      # Only install if the .nupkg file does not already exists.
      nupkg_file = dep.nupkg(artifacts_dir)
      if not path.isfile(nupkg_file):
        command = self.csc.get_nuget() + ['install', dep.id, '-Version', dep.version]
        subprocess.check_call(command, cwd=artifacts_dir)

      # Parse the .nuspec for this package's dependencies.
      specdom = nupkg.get_nuspec(nupkg_file)
      if not specdom:
        log.warn('Could not read .nuspec from "{}"'.format(nupkg_file))
        continue

      # XXX determine target_framework, None includes ALL dependencies (which is bad)
      target_framework = None
      for dep in nupkg.nuspec_eval_deps(specdom, target_framework):
        deps.add(dep)

    for dep in deps:
      filename = dep.resolve(artifacts_dir, framework=self.csc.netversion)
      if filename is not None:
        result.append(filename)
    return result


csc = CscInfo.get()
print('{} v{}'.format('CSC' if csc.impl == 'net' else csc.impl, csc.version))

context.register_handler(CsharpTargetHandler(csc))

# The Craftr build system
# Copyright (C) 2016  Niklas Rosenstein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from craftr import core
from craftr.core.config import read_config_file, InvalidConfigError
from craftr.core.logging import logger
from craftr.core.session import session, Session, Module, MANIFEST_FILENAMES
from craftr.utils import path, shell, tty
from operator import attrgetter
from nr.types.version import Version, VersionCriteria

import abc
import argparse
import atexit
import configparser
import craftr.defaults
import craftr.targetbuilder
import functools
import json
import os
import sys
import textwrap

CONFIG_FILENAME = '.craftrconfig'
INIT_DIR = path.getcwd()


def textfill(text, width=None, indent=0, fillchar=' '):
  prefix = fillchar * indent
  return prefix + ('\n' + prefix).join(textwrap.wrap(text))

def parse_cmdline_options(options):
  for item in options:
    key, sep, value = item.partition('=')
    if not sep:
      value = 'true'
    if not value:
      session.options.pop(key, None)
    else:
      session.options[key] = value


def read_cache(cachefile):
  try:
    with open(cachefile) as fp:
      try:
        session.read_cache(fp)
      except ValueError as exc:
        return False
  except IOError as exc:
    return False
  return True


def write_cache(cachefile):
  # Write back the cache.
  try:
    path.makedirs(path.dirname(cachefile))
    with open(cachefile, 'w') as fp:
      session.write_cache(fp)
  except OSError as exc:
    logger.error('error writing cache file:', cachefile)
    logger.error(exc, indent=1)
  else:
    logger.debug('cache written:', cachefile)


def serialise_loaded_module_info():
  """
  Converts all modules that have been loaded into the active session a JSON
  serialisable object that can be saved into the Craftr cache. This cache
  object contains the same nested structures as :attr:`Session.modules`.

  This cache is loaded when the exported project is being built to register
  when files have changed. Note that the modification time that is saved
  is the sum of all dependent files.

  Example:

  .. code:: json

    "modules": {
      "craftr.lang.cxx.msvc": {
        "1.0.0": {
          "deps": [
            "c:\\users\\niklas\\repos\\craftr\\craftr\\stl\\craftr.lang.cxx.msvc\\manifest.json",
            "c:\\users\\niklas\\repos\\craftr\\craftr\\stl\\craftr.lang.cxx.msvc\\craftrfile"
          ],
          "mtime": 2962706318
        }
      },
      "craftr.lib.sdl2": {
        "1.0.0": {
          "deps": [
            "c:\\users\\niklas\\repos\\craftr\\craftr\\stl_auxiliary\\craftr.lib.sdl2\\manifest.json",
            "c:\\users\\niklas\\repos\\craftr\\craftr\\stl_auxiliary\\craftr.lib.sdl2\\craftrfile"
          ],
          "mtime": 2963870114
        }
      },
      "craftr.lang.cxx": {
        "1.0.0": {
          "deps": [
            "c:\\users\\niklas\\repos\\craftr\\craftr\\stl\\craftr.lang.cxx\\manifest.json",
            "c:\\users\\niklas\\repos\\craftr\\craftr\\stl\\craftr.lang.cxx\\craftrfile"
          ],
          "mtime": 2963324399
        }
      },
      "examples.c-sdl2": {
        "1.0.0": {
          "deps": [
            "c:\\users\\niklas\\repos\\craftr\\examples\\examples.c-sdl2\\manifest.json",
            "c:\\users\\niklas\\repos\\craftr\\examples\\examples.c-sdl2\\craftrfile"
          ],
          "mtime": 2963870114
        }
      }
    }
  """

  modules = {}
  for name, versions in session.modules.items():
    module_versions = {}
    for version, module in versions.items():
      if not module.executed: continue
      module_versions[str(version)] = {
        "deps": module.dependent_files,
        "mtime": sum(map(path.getimtime, module.dependent_files))
      }
    if module_versions:
      modules[name] = module_versions
  return modules


def unserialise_loaded_module_info(modules):
  """
  This function takes the data generated with :func:`serialise_loaded_module_info`
  and converts it back to a format that is easier to use later in the build process.
  Currently, this function only converts the version-number fields to actual
  :class:`Version` objects and adds a ``"changed"`` key to a module based on
  the ``"mtime"`` and the current modification times of the files.
  """

  result = {}
  for name, versions in modules.items():
    result[name] = {}
    for version, module in versions.items():
      version = Version(version)
      result[name][version] = module
      mtime = 0
      for fn in module['deps']:
        try:
          mtime += path.getimtime(fn)
        except OSError:
          mtime = 0
          break
      module['changed'] = (mtime != module['mtime'])
  return result


def parse_module_spec(spec):
  """
  Parses a module spec as it can be specified on the command-line. The
  format is ``module_name[:version]``.
  """

  parts = spec.split(':')
  if len(parts) not in (1, 2):
    raise ValueError('invalid module spec: {!r}'.format(spec))
  if len(parts) == 1:
    parts.append('*')
  try:
    version = Version(parts[1])
  except ValueError as exc:
    version = VersionCriteria(parts[1])
  return parts[0], version


def get_volatile_module_version(name):
  """
  Given a module name of which the exact version number may be appended
  and separated by a hyphen, returns the raw module name and its version
  as a tuple. If the module is not suffixed with a version number, the
  returned version number is :const:`None` instead.
  """

  parts = name.rpartition('-')[::2]
  if len(parts) != 2:
    return name
  try:
    version = Version(parts[1])
  except ValueError:
    version = None
  else:
    name = parts[0]
  return name, version


@functools.lru_cache()
def get_ninja_version(ninja_bin):
  ''' Read the ninja version from the `ninja` program and return it. '''

  return shell.pipe([ninja_bin, '--version'], shell=True).output.strip()


def get_ninja_info():
  # Make sure the Ninja executable exists and find its version.
  ninja_bin = session.options.get('global.ninja') or \
      session.options.get('craftr.ninja') or os.getenv('NINJA', 'ninja')
  ninja_bin = shell.find_program(ninja_bin)
  ninja_version = get_ninja_version(ninja_bin)
  logger.debug('Ninja executable:', ninja_bin)
  logger.debug('Ninja version:', ninja_version)
  return ninja_bin, ninja_version


def finally_(finally_func):
  """
  Decorator that calls *finally_func* after the decorated function.
  """

  def decorator(func):
    def wrapper(*args, **kwargs):
      try:
        return func(*args, **kwargs)
      finally:
        finally_func(*args, **kwargs)
    return wrapper
  return decorator


class BaseCommand(object, metaclass=abc.ABCMeta):
  """
  Base class for Craftr subcommands.
  """

  @abc.abstractmethod
  def build_parser(self, parser):
    pass

  @abc.abstractmethod
  def execute(self, parser, args):
    pass



class BuildCommand(BaseCommand):

  def __init__(self, mode):
    assert mode in ('clean', 'build', 'export', 'run', 'help',
                    'dump-options', 'dump-deptree')
    self.mode = mode

  def build_parser(self, parser):
    add_arg = parser.add_argument

    # Inherit options from main parser so they can also be specified
    # after the sub-command.
    add_arg('-v', '--verbose', action='store_true')

    if self.mode not in ('dump-options', 'dump-deptree'):
      add_arg('-d', '--option', dest='options', action='append', default=[])

    if self.mode in ('export', 'run', 'help', 'dump-options', 'dump-deptree'):
      add_arg('-m', '--module')
      add_arg('-i', '--include-path', action='append', default=[])
    elif self.mode in ('build', 'clean'):
      add_arg('targets', metavar='TARGET', nargs='*')

    if self.mode == 'run':
      add_arg('task', nargs='?')
      add_arg('task_args', nargs='*')

    if self.mode == 'dump-options':
      add_arg('-r', '--recursive', action='store_true')
      add_arg('-d', '--details', action='store_true')

    if self.mode == 'clean':
      add_arg('-r', '--recursive', action='store_true')

    if self.mode == 'help':
      add_arg('name', help='The name of the symbols to show help for. Must be '
        'in the format <module>:<symbol> where <module> is the name of a '
        'Craftr module. The <module>: bit is optiona. If only <symbol> is '
        'specified and is built-in name, nothing will be executed. Otherwise, '
        'the <module>: bit will default to the current main module.',
        nargs='?')

    add_arg('-b', '--build-dir', default='build')

  def __cleanup(self, parser, args):
    """
    Switch back to the original directory and check if we can clean up
    the build directory.
    """

    os.chdir(session.maindir)
    if os.path.isdir(session.builddir) and not os.listdir(session.builddir):
      logger.debug('note: cleanup empty build directory:', session.builddir)
      os.rmdir(session.builddir)

  @finally_(__cleanup)
  def execute(self, parser, args):
    if hasattr(args, 'include_path'):
      session.path.extend(map(path.norm, args.include_path))

    # Help-command preprocessing. Check if we're to show the help on a builtin
    # object, otherwise extract the module name if applicable.
    if self.mode == 'help':
      if not args.name:
        help('craftr')
        return 0
      if args.name in vars(craftr.defaults):
        help(getattr(craftr.defaults, args.name))
        return 0
      # Check if we have an absolute symbol reference.
      if ':' in args.name:
        if args.module:
          parser.error('-m/--module option conflicting with name argument: "{}"'
            .format(args.name))
        args.module, args.name = args.name.split(':', 1)

    module = self._find_module(parser, args)
    session.main_module = module
    self.ninja_bin, self.ninja_version = get_ninja_info()

    # Create and switch to the build directory.
    session.builddir = path.abs(path.norm(args.build_dir, INIT_DIR))
    path.makedirs(session.builddir)
    os.chdir(session.builddir)
    self.cachefile = path.join(session.builddir, '.craftrcache')

    # Prepare options, loaders and execute.
    if self.mode in ('export', 'run', 'help'):
      return self._export_run_or_help(args, module)
    elif self.mode == 'dump-options':
      return self._dump_options(args, module)
    elif self.mode == 'dump-deptree':
      return self._dump_deptree(args, module)
    elif self.mode in ('build', 'clean'):
      return self._build_or_clean(args)
    else:
      raise RuntimeError("mode: {}".format(self.mode))

  def _find_module(self, parser, args):
    """
    Find the main Craftr module that is to be executed. Returns None in
    modes that do not require a main module.
    """

    if self.mode not in ('export', 'run', 'help', 'dump-options', 'dump-deptree'):
      return None

    # Determine the module to execute, either from the current working
    # directory or find it by name if one is specified.
    if not args.module:
      for fn in MANIFEST_FILENAMES + [path.join('craftr', x) for x in MANIFEST_FILENAMES]:
        if path.isfile(fn):
          module = session.parse_manifest(fn)
          break
      else:
        logger.error('"{}" does not exist'.format(MANIFEST_FILENAMES[0]))
        sys.exit(1)
    else:
      # TODO: For some reason, prints to stdout are not visible here.
      # TODO: Prints to stderr however work fine.
      try:
        module_name, version = parse_module_spec(args.module)
      except ValueError as exc:
        logger.error('{} (note: you have to escape > and < characters)'.format(exc))
        sys.exit(1)
      try:
        module = session.find_module(module_name, version)
      except Module.NotFound as exc:
        logger.error('module not found: ' + str(exc))
        sys.exit(1)

    return module

  def _export_run_or_help(self, args, module):
    """
    Called when the mode is 'export' or 'run'. Will execute the specified
    *module* and eventually export a Ninja manifest and Cache.
    """

    read_cache(self.cachefile)

    session.expand_relative_options()
    session.cache['build'] = {}
    try:
      module.run()
    except Module.InvalidOption as exc:
      for error in exc.format_errors():
        logger.error(error)
      return 1
    except craftr.defaults.ModuleError as exc:
      logger.error('error:', exc)
      return 1
    finally:
      if sys.exc_info() and self.mode == 'export':
        # We still want to write the cache, especially so that data already
        # loaded with loaders doesn't need to be re-loaded. They'll find out
        # when the cached information was not valid.
        write_cache(self.cachefile)

    # Fill the cache.
    session.cache['build']['targets'] = list(session.graph.targets.keys())
    session.cache['build']['modules'] = serialise_loaded_module_info()
    session.cache['build']['main'] = module.ident
    session.cache['build']['options'] = args.options

    if self.mode == 'export':
      # Add the Craftr_run_command variable which is necessary for tasks
      # to properly executed.
      run_command = ['craftr', '-q', '-P', path.rel(session.maindir)]
      if args.no_config: run_command += ['-C']
      run_command += ['-c' + x for x in args.config]
      run_command += ['run']
      if args.module: run_command += ['-m', args.module]
      run_command += ['-i' + x for x in args.include_path]
      run_command += ['-b', path.rel(session.builddir)]
      session.graph.vars['Craftr_run_command'] = shell.join(run_command)

      write_cache(self.cachefile)

      # Write the Ninja manifest.
      with open("build.ninja", 'w') as fp:
        platform = core.build.get_platform_helper()
        context = core.build.ExportContext(self.ninja_version)
        writer = core.build.NinjaWriter(fp)
        session.graph.export(writer, context, platform)
        logger.info('exported "build.ninja"')
      return 0

    elif self.mode == 'run':
      if args.task:
        if args.task not in session.graph.tasks:
          logger.error('no such task exists: "{}"'.format(args.task))
          return 1
        task = session.graph.tasks[args.task]
        return task.invoke(args.task_args)
      return 0

    elif self.mode == 'help':
      if args.name not in vars(module.namespace):
        logger.error('symbol not found: "{}:{}"'.format(
          module.manifest.name, args.name))
        return 1
      help(getattr(module.namespace, args.name))
      return 0

    assert False, "unhandled mode: {}".format(self.mode)

  def _dump_options(self, args, module):
    width = tty.terminal_size()[0]

    print()
    title = '{} (v{})'.format(module.manifest.name, module.manifest.version)
    print(title)

    if args.details:
      print('-' * len(title))
      print()
      if module.manifest.description:
        print('Description:\n')
        print(textfill(module.manifest.description, indent = 2))
        print()

      print('Options:\n')

    for option in sorted(module.manifest.options.values(), key = attrgetter('name')):
      line = '  ' + option.name
      info = option.alias
      if option.inherit:
        info += ', inheritable'
      remain = width - len(line) - len(info)
      default = repr(option.default)
      default_inline = False
      if len(default) < (remain - 4): # 3 spaces and 2 parenthesis
        default_inline = True
        info = '({}) '.format(default) + info
        remain -= len(default) + 3

      print(line + ' ' * remain + info)
      if not default_inline:
        print('    ({})'.format(default))
      if args.details:
        if option.help:
          print()
          print(textfill(option.help, indent = 4))
        print()

    if args.recursive:
      for name, version in module.manifest.dependencies.items():
        print()
        self._dump_options(args, session.find_module(name, version))
    return 0

  def _dump_deptree(self, args, module, indent=0, index=0):
    if indent == 0 and index == 0:
      print()
    print('  ' * indent + '{} (v{})'.format(module.manifest.name, module.manifest.version))
    for index, (name, version) in enumerate(module.manifest.dependencies.items()):
      self._dump_deptree(args, session.find_module(name, version), indent=indent+1, index=index)
    return 0

  def _build_or_clean(self, args):
    """
    Will be called for the 'build' and 'clean' modes. Loads the Craftr
    cache and invokes Ninja.
    """

    # Read the cache and parse command-line options.
    if not read_cache(self.cachefile):
      logger.error('Unable to find file: .craftrcache')
      logger.error('Does not seemt to be a build directory: {}'.format(session.builddir))
      logger.error("Export build information using the 'craftr export' command.")
      return 1

    parse_cmdline_options(session.cache['build']['options'])
    main = session.cache['build']['main']
    available_targets = frozenset(session.cache['build']['targets'])
    available_modules = unserialise_loaded_module_info(session.cache['build']['modules'])

    logger.debug('build main module:', main)
    session.expand_relative_options(get_volatile_module_version(main)[0])

    # Check if any of the modules changed, so we can let the user know he
    # might have to re-export the build files.
    changed_modules = []
    for name, versions in available_modules.items():
      for version, info in versions.items():
        if info['changed']:
          changed_modules.append('{}-{}'.format(name, version))
    if changed_modules:
      if len(changed_modules) == 1:
        logger.info('note: module "{}" has changed, maybe you should re-export'.format(changed_modules[0]))
      else:
        logger.info('note: some modules have changed, maybe you should re-export')
        for name in changed_modules:
          logger.info('  -', name)

    # Check the targets and if they exist.
    targets = []
    for target_name in args.targets:
      if '.' not in target_name:
        target_name = main + '.' + target_name
      elif target_name.startswith('.'):
        target_name = main + target_name

      module_name, target_name = target_name.rpartition('.')[::2]
      module_name, version = get_volatile_module_version(module_name)

      if module_name not in available_modules:
        error('no such module:', module_name)
      if not version:
        version = max(available_modules[module_name].keys())

      target_name = craftr.targetbuilder.get_full_name(
          target_name, module_name=module_name, version=version)
      if target_name not in available_targets:
        parser.error('no such target: {}'.format(target_name))
      targets.append(target_name)

    # Make sure we get all the output before running the subcommand.
    logger.flush()

    # Execute the ninja build.
    cmd = [self.ninja_bin]
    if args.verbose:
      cmd += ['-v']
    if self.mode == 'clean':
      cmd += ['-t', 'clean']
      if not args.recursive:
        cmd += ['-r']
    cmd += targets
    return shell.run(cmd).returncode


class StartpackageCommand(BaseCommand):

  def build_parser(self, parser):
    parser.add_argument('name')
    parser.add_argument('directory', nargs='?', default=None)
    parser.add_argument('-n', '--nested', action='store_true')
    parser.add_argument('--version', type=Version, default='1.0.0')
    parser.add_argument('-f', '--format', choices=['cson', 'json'], default='cson')

  def execute(self, parser, args):
    directory = args.directory or args.name
    if path.maybedir(directory):
      directory = path.join(directory, args.name)

    if not path.exists(directory):
      logger.debug('creating directory "{}"'.format(directory))
      path.makedirs(directory)
    elif not path.isdir(directory):
      logger.error('"{}" is not a directory'.format(directory))
      return 1

    if args.nested:
      directory = path.join(directory, 'craftr')
      path.makedirs(directory)

    mfile = path.join(directory, 'manifest.' + args.format)
    sfile = path.join(directory, 'Craftrfile')
    for fn in [mfile, sfile]:
      if path.isfile(fn):
        logger.error('"{}" already exists'.format(fn))
        return 1


    logger.debug('creating file "{}"'.format(mfile))
    with open(mfile, 'w') as fp:
      if args.format == 'cson':
        lines = textwrap.dedent('''
          name: "%s"
          version: "%s"
          project_dir: ".."
          author: ""
          url: ""
          dependencies: {}
          options: {}
        ''' % (args.name, args.version)).lstrip().split('\n')
        if not args.nested:
          del lines[2]
      elif args.format == 'json':
        lines = textwrap.dedent('''
          {
            "name": "%s",
            "version": "%s",
            "project_dir": "..",
            "author": "",
            "url": "",
            "dependencies": {},
            "options": {}
          }''' % (args.name, args.version)).lstrip().split('\n')
        if not args.nested:
          del lines[3]
      fp.write('\n'.join(lines))

    logger.debug('creating file "{}"'.format(sfile))
    with open(sfile, 'w') as fp:
      print('# {}'.format(args.name), file=fp)


class VersionCommand(BaseCommand):

  def build_parser(self, parser):
    pass

  def execute(self, parser, args):
    print(craftr.__version__)


def main():
  # Create argument parsers and dynamically include all BaseCommand
  # subclasses into it.
  parser = argparse.ArgumentParser(prog='craftr', description='The Craftr build system')
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('-q', '--quiet', action='store_true')
  parser.add_argument('-c', '--config', action='append', default=[])
  parser.add_argument('-C', '--no-config', action='store_true')
  parser.add_argument('-P', '--project-dir')
  parser.add_argument('-d', '--option', dest='options', action='append', default=[])
  subparsers = parser.add_subparsers(dest='command')

  commands = {
    'clean': BuildCommand('clean'),
    'build': BuildCommand('build'),
    'export': BuildCommand('export'),
    'run': BuildCommand('run'),
    'help': BuildCommand('help'),
    'options': BuildCommand('dump-options'),
    'deptree': BuildCommand('dump-deptree'),
    'startpackage': StartpackageCommand(),
    'version': VersionCommand()
  }

  for key, cmd in commands.items():
    cmd.build_parser(subparsers.add_parser(key))

  # Parse the arguments.
  args = parser.parse_args()
  if not args.command:
    parser.print_usage()
    return 0

  if args.project_dir:
    os.chdir(args.project_dir)
  if args.verbose:
    logger.set_level(logger.DEBUG)
  elif args.quiet:
    logger.set_level(logger.WARNING)

  session = Session()

  # Parse the user configuration file.
  try:
    config_filename = path.expanduser('~/' + CONFIG_FILENAME)
    session.options = read_config_file(config_filename)
  except FileNotFoundError as exc:
    session.options = {}
  except InvalidConfigError as exc:
    parser.error(exc)
    return 1

  # Parse the local configuration file or the ones specified on command-line.
  if not args.no_config:
    try:
      for filename in args.config:
        session.options.update(read_config_file(filename))
      if not args.config:
        choices = [CONFIG_FILENAME, path.join('craftr', CONFIG_FILENAME)]
        for fn in choices:
          try:
            session.options.update(read_config_file(fn))
          except FileNotFoundError as exc:
            pass
    except InvalidConfigError as exc:
      parser.error(exc)
      return 1

  # Execute the command in the session context.
  with session:
    parse_cmdline_options(args.options)
    return commands[args.command].execute(parser, args)


def main_and_exit():
  sys.exit(main())


if __name__ == '__main__':
  main_and_exit()

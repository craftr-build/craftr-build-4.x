
"""
Provides the C++ build configuration tools.
"""

import abc
import enum
import typing as t
from pathlib import Path

from craftr.core import Action, HavingProperties, Project, Property, Task
from craftr.core.actions import CommandAction, CreateDirectoryAction
from craftr.core.types import File
from craftr.stdlib.cxx.namingscheme import NamingScheme
from craftr.stdlib.interfaces.executable import IExecutableProvider, ExecutableInfo

from .interfaces import CxxLibraryInfo, ICxxLibraryProvider


class CxxLibraryType(enum.Enum):
  static = enum.auto()
  shared = enum.auto()


class CxxBuilderBaseProps(HavingProperties):
  """ Base props for building C/C++ libraries or applications. """

  naming_scheme: NamingScheme = NamingScheme.CURRENT
  sources: t.Annotated[Property[t.List[File]], Task.Input]
  include_paths: t.Annotated[Property[t.List[File]], Task.Input]
  build_options: Property[t.List[str]]


class CxxApplicationProps(CxxBuilderBaseProps):
  executable_name: t.Annotated[Property[str], Task.Output]
  executable_path: t.Annotated[Property[File], Task.Output]


class CxxLibraryProps(CxxBuilderBaseProps):
  public_include_paths: Property[t.List[File]]
  library_type: Property[CxxLibraryType]
  library_name: t.Annotated[Property[str], Task.Output]
  library_path: t.Annotated[Property[File], Task.Output]


class CppProps(HavingProperties):
  pass


class CxxBaseTask(Task, CxxBuilderBaseProps, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def _get_cxx_output_file(self) -> Path:
    pass

  def _get_preferred_output_directory(self) -> Path:
    return self.project.build_directory / self.name

  def get_actions(self) -> t.List['Action']:
    object_dir = self._get_preferred_output_directory() / 'obj'
    product_filename = self._get_cxx_output_file()

    include_paths: t.List[File] = self.include_paths.or_else([])
    static_libs: t.List[str] = []

    # Collect libraries from dependencies.
    # TODO(NiklasRosenstein): Collect dependencies transitively?
    for dep in self.get_dependencies():
      if isinstance(dep, ICxxLibraryProvider):
        info = dep.get_cxx_library_info()
        include_paths += info.include_paths
        static_libs += info.library_files

    flags: t.List[str] = []
    is_static = False
    if isinstance(self, CxxLibraryProps):
      library_type = self.library_type.or_else(CxxLibraryType.static)
      if library_type == CxxLibraryType.shared:
        flags += ['-shared']
      elif library_type == CxxLibraryType.static:
        is_static = True
    for path in include_paths:
      flags.append('-I' + str(path))

    actions: t.List[Action] = []
    actions.append(CreateDirectoryAction(object_dir))
    actions.append(CreateDirectoryAction(product_filename.parent))

    # Generate actions to compile object files.
    compiler = 'g++' if isinstance(self, CppProps) else 'gcc'
    object_files: t.List[str] = []
    for source_file in self.sources.get():
      object_file = (object_dir / Path(source_file).name).with_suffix('.o')
      object_files.append(str(object_file))
      compile_command = [compiler] + flags + ['-c', str(source_file), '-o', str(object_file)]
      actions.append(CommandAction(command=compile_command))


    if is_static:
      archive_command = ['ar', 'rcs', str(product_filename)] + object_files
      actions.append(CommandAction(command=archive_command))
    else:
      linker_command = [compiler] + flags + object_files + static_libs + ['-o', str(product_filename)]
      actions.append(CommandAction(command=linker_command))

    return actions


class CxxApplicationTask(CxxBaseTask, CxxApplicationProps, IExecutableProvider):

  def get_executable_name(self) -> str:
    name = self.executable_name.or_else(self.project.name)
    return name + self.naming_scheme['e']

  def get_executable_path(self) -> Path:
    return Path(self.executable_path.or_else_get(
        lambda: self._get_preferred_output_directory() / self.get_executable_name()))

  # CxxBaseTask
  _get_cxx_output_file = get_executable_path

  # IExecutableProvider
  def get_executable_info(self) -> ExecutableInfo:
    return ExecutableInfo(str(self.get_executable_path()))


class CxxLibraryTask(CxxLibraryProps, CxxBaseTask, ICxxLibraryProvider):

  def get_library_name(self) -> str:
    name = self.library_name.or_else(self.project.name)
    return self.naming_scheme['lp'] + name + self.naming_scheme['ls']

  def get_library_path(self) -> Path:
    path = self.library_path.map(Path).or_else(None)
    if path is None:
      path = Path(self._get_preferred_output_directory() / self.get_library_name())
    return path

  # CxxBaseTask
  _get_cxx_output_file = get_library_path

  # ICxxLibraryProvider
  def get_cxx_library_info(self) -> CxxLibraryInfo:
    include_paths = list(map(str, self.public_include_paths.or_else_get(lambda: self.include_paths.or_else([]))))
    return CxxLibraryInfo(self.path, [str(self.get_library_path())], include_paths)


class CApplicationTask(CxxApplicationTask):
  pass


class CppApplicationTask(CppProps, CxxApplicationTask):
  pass


class CLibraryTask(CxxLibraryTask):
  pass


class CppLibraryTask(CxxLibraryTask):
  pass


def apply(project: Project):
  project.add_task_extension('c_application', CApplicationTask)
  project.add_task_extension('cpp_application', CppApplicationTask)
  project.add_task_extension('c_library', CLibraryTask)
  project.add_task_extension('cpp_library', CppLibraryTask)

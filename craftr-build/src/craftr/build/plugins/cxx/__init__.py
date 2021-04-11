
"""
Provides the C++ build configuration tools.
"""

import abc
import enum
import typing as t
from pathlib import Path

from craftr.build.lib import IExecutableProvider, ExecutableInfo, INativeLibProvider, PluginRegistration
from craftr.build.lib.interfaces.native import NativeLibInfo
from craftr.core import Action, HavingProperties, Property, Task
from craftr.core.actions import CommandAction, CreateDirectoryAction
from craftr.core.types import File
from .namingscheme import NamingScheme

plugin = PluginRegistration()
apply = plugin.apply


@plugin.exports
class ProductType(enum.Enum):
  OBJECTS = enum.auto()
  EXECUTABLE = enum.auto()
  STATIC = enum.auto()
  SHARED = enum.auto()

  @property
  def is_lib(self) -> bool:
    return self in (ProductType.SHARED, ProductType.STATIC)


@plugin.exports
class Language(enum.Enum):
  C = enum.auto()
  CPP = enum.auto()


class Props(HavingProperties):
  """ Base props for building C/C++ libraries or applications. """

  naming_scheme: NamingScheme = NamingScheme.CURRENT
  sources: t.Annotated[Property[t.List[File]], Task.Input]
  include_paths: Property[t.List[File]]
  public_include_paths: Property[t.List[File]]
  build_options: Property[t.List[str]]
  language: Property[Language]
  product_name: Property[str]
  product_type: Property[ProductType]
  outputs: t.Annotated[Property[t.List[File]], Task.Output]


@plugin.exports('compile')
class Compile(Task, Props, IExecutableProvider, INativeLibProvider, metaclass=abc.ABCMeta):

  def _get_preferred_output_directory(self) -> Path:
    return self.project.build_directory / self.name

  def _get_executable_name(self) -> str:
    assert self.product_type.get() == ProductType.EXECUTABLE, self.product_type.get()
    return self.product_name.get() + self.naming_scheme['e']

  def _get_executable_path(self) -> str:
    return str(self._get_preferred_output_directory() / self._get_executable_name())

  def _get_library_name(self) -> str:
    assert self.product_type.get().is_lib, self.product_type.get()
    return self.naming_scheme['lp'] + self.product_name.get() + self.naming_scheme['ls']

  def _get_library_path(self) -> str:
    return str(self._get_preferred_output_directory() / self._get_library_name())

  def _get_objects_output_directory(self) -> Path:
    return self._get_preferred_output_directory() / 'obj'

  def _get_objects_paths(self) -> t.List[str]:
    object_dir = self._get_objects_output_directory()
    return [str((object_dir / Path(f).name).with_suffix(self.naming_scheme['o'])) for f in self.sources.get()]

  def _detect_language(self, source_file: str) -> str:
    if source_file.endswith('.cpp') or source_file.endswith('.cc'):
      return Language.CPP
    else:
      return Language.C

  def _get_compiler(self, language: Language) -> str:
    return 'g++' if language == Language.CPP else 'gcc'

  # IExecutableProvider
  def get_executable_info(self) -> ExecutableInfo:
    if self.product_type.get() == ProductType.EXECUTABLE:
      return ExecutableInfo(self._get_executable_path())
    return None

  # INativeLibProvider
  def get_native_lib_info(self) -> t.Optional[NativeLibInfo]:
    if self.product_type.get().is_lib:
      include_paths = list(map(str, self.public_include_paths.or_else_get(lambda: self.include_paths.or_else([]))))
      return NativeLibInfo(name=self.path, library_files=[self._get_library_path()], include_paths=include_paths)
    return None

  # Task
  def init(self) -> None:
    self.product_name.set_default(lambda: self.project.name)
    self.product_type = ProductType.EXECUTABLE

  # Task
  def finalize(self) -> None:
    if self.product_type.get() == ProductType.EXECUTABLE:
      self.outputs = [self._get_executable_path()]
    elif self.product_type.get().is_lib:
      self.outputs = [self._get_library_path()]
    elif self.product_type.get() == ProductType.OBJECTS:
      self.outputs = self._get_objects_paths()
    else: assert False, self.product_type
    super().finalize()

  # Task
  def get_actions(self) -> t.List['Action']:
    # Collect native libs from dependencies.
    # TODO(nrosenstein): Transitive dependencies?
    native_deps: t.List[NativeLibInfo] = []
    for dep in self.get_dependencies():
      if isinstance(dep, INativeLibProvider):
        info = dep.get_native_lib_info()
        if info is not None:
          native_deps.append(info)

    # Collect the include paths.
    include_paths = self.include_paths.or_else([]) + self.public_include_paths.or_else([])

    # Generate the compiler flags.
    flags: t.List[str] = []
    if self.product_type.get() == ProductType.SHARED:
      flags += ['-shared', '-fPIC']
    for path in include_paths:
      flags.append('-I' + str(path))

    actions: t.List[Action] = []
    actions.append(CreateDirectoryAction(self._get_preferred_output_directory()))
    actions.append(CreateDirectoryAction(self._get_objects_output_directory()))

    # Generate actions to compile object files.
    languages: t.Set[Language] = set()
    object_files = self._get_objects_paths()
    for source_file, object_file in zip(map(str, self.sources.get()), object_files):
      language = self.language.or_else_get(lambda: self._detect_language(source_file))
      compiler = self._get_compiler(language)
      compile_command = [compiler] + flags + ['-c', source_file, '-o', object_file]
      actions.append(CommandAction(command=compile_command))
      languages.add(language)

    # Generate the archive or link action.
    if self.product_type.get() == ProductType.STATIC:
      archive_command = ['ar', 'rcs', self._get_library_path()] + self._get_objects_paths()
      actions.append(CommandAction(command=archive_command))
    elif self.product_type.get() != ProductType.OBJECTS:
      if self.product_type.get() == ProductType.EXECUTABLE:
        product_filename = self._get_executable_path()
      elif self.product_type.get() == ProductType.SHARED:
        product_filename = self._get_library_path()
      else: assert False, self.product_type.get()
      static_libs = [y for x in native_deps for y in x.library_files]
      linker_command = [compiler] + flags + object_files + static_libs + ['-o', str(product_filename)]
      actions.append(CommandAction(command=linker_command))

    return actions

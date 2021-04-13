
import abc
import typing as t
from dataclasses import dataclass, field


@dataclass
class ExecutableInfo:
  #: The path to the executable file.
  filename: str

  #: A list of files or directories that are considered required dependencies for the
  #: executable. The paths must already be in their expected arrangement relative to the
  #: executable file.
  dependencies: t.List[str] = field(default_factory=list)

  #: An optional list of command-line arguments to use when invoking the executable. The
  #: first argument in this list is the program that will actually be executed. If set, the
  #: #filename should usually be included in this list of arguments one way or another. If not
  #: set, it is assumed that the #filename is executable directly.
  invokation_layout: t.Optional[t.List[str]] = None


@t.runtime_checkable
class IExecutableProvider(t.Protocol, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def get_executable_info(self) -> t.Optional[ExecutableInfo]:
    pass


@dataclass
class NativeLibInfo:
  #: Simple readable name of the native library.
  name: str

  #: A list of filenames for the native library.
  library_files: t.List[str] = field(default_factory=list)

  #: A list of library search paths:
  library_search_paths: t.List[str] = field(default_factory=list)

  #: A list of library names from the search paths.
  library_names: t.List[str] = field(default_factory=list)

  #: Public include directories for using the library.
  include_paths: t.List[str] = field(default_factory=list)

  #: Defines for using the library.
  defines: t.List[str] = field(default_factory=list)

  #: A list of compiler flags.
  compiler_flags: t.List[str] = field(default_factory=list)

  #: A list of linker flags.
  linker_flags: t.List[str] = field(default_factory=list)


@t.runtime_checkable
class INativeLibProvider(t.Protocol, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def get_native_lib_info(self) -> t.Optional[NativeLibInfo]:
    pass

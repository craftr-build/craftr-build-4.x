
import abc
import typing as t
from dataclasses import dataclass


@dataclass
class CxxLibraryInfo:
  name: str
  library_files: t.List[str]
  include_paths: t.List[str]


@t.runtime_checkable
class ICxxLibraryProvider(t.Protocol, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def get_cxx_library_info(self) -> CxxLibraryInfo:
    pass

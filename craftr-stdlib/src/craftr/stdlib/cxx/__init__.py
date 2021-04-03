
"""
Provides the C++ build configuration tools.
"""

import typing as t
from pathlib import Path

from craftr.core import Action, Project, Property, Task
from craftr.core.actions import CommandAction, CreateDirectoryAction
from craftr.core.types import File
from craftr.stdlib.interfaces.executable import IExecutableProvider, ExecutableInfo


class CxxApplicatonTask(Task, IExecutableProvider):

  sources: t.Annotated[Property[t.List[File]], Task.Input]
  include_paths: t.Annotated[Property[t.List[File]], Task.Input]

  executable_name: t.Annotated[Property[File], Task.Output]
  executable_path: t.Annotated[Property[File], Task.Output]

  def get_executable_path(self) -> Path:
    return Path(self.executable_path.or_else_get(
        lambda: self.project.build_directory / self.name /
            self.executable_name.or_else(self.project.name)))

  def get_actions(self) -> t.List['Action']:
    executable_path = self.get_executable_path()
    command = ['g++'] + list(map(str, self.sources.get())) + ['-o', str(executable_path)]
    return [
      CreateDirectoryAction(executable_path.parent),
      CommandAction(command=command),
    ]

  def get_executable_info(self) -> ExecutableInfo:
    return ExecutableInfo(str(self.get_executable_path()))


def apply(project: Project):
  project.add_task_extension('cxx_application', CxxApplicatonTask)

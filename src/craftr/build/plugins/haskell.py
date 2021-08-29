
"""
Provides a simple interface to building Haskell applications.
"""

import os
from pathlib import Path
import typing as t
import typing_extensions as te

from craftr.core import Project, Property, Task, Namespace
from craftr.core.actions import CreateDirectoryAction, CommandAction
from craftr.core.actions.action import Action


class HaskellApplicationTask(Task):

  output_file: te.Annotated[Property[Path], Task.Output]
  srcs: te.Annotated[Property[t.List[Path]], Task.InputFile]
  compiler_flags: Property[t.List[str]]

  # Properties that construct the output filename.
  output_directory: Property[Path]
  product_name: Property[str]
  suffix: Property[str]

  def init(self) -> None:
    self.output_directory.set_default(lambda: self.project.build_directory / 'haskell' / self.name)
    self.product_name.set_default(lambda: 'main')
    self.suffix.set_default(lambda: '.exe' if os.name == 'nt' else '')
    self.output_file.set_default(lambda: self.output_directory.get() / (self.product_name.get() + self.suffix.get()))
    self.run = self.project.task(self.name + 'Run')
    self.run.group = 'run'
    self.run.default = False
    self.run.always_outdated = True
    self.run.depends_on(self)

  def finalize(self) -> None:
    super().finalize()
    self.run.do_last(CommandAction([str(self.output_file.get())]))

  def get_actions(self) -> t.List['Action']:
    output_file = self.output_file.get()
    srcs = list(map(str, self.srcs.get()))
    command = ['ghc', '-o', str(output_file)] + srcs + self.compiler_flags.or_else([])

    actions: t.List[Action] = [
      CreateDirectoryAction(output_file.parent),
      CommandAction(command),
    ]

    # TODO(nrosenstein): Add cleanup action to remove .hi/.o files?
    #   There doesn't seem to be an option in the Ocaml compiler to change their
    #   output location.

    return actions


def apply(project: Project, namespace: Namespace) -> None:
  namespace.add('HaskellApplicationTask', HaskellApplicationTask)
  namespace.add_task_factory('haskellApplication', HaskellApplicationTask)


"""
Provides a simple interface to building Haskell applications.
"""

import os
import typing as t
import typing_extensions as te
from craftr.build.lib.helpers import TaskFactoryExtension

from craftr.core import Project, Property, Task
from craftr.core.actions import CreateDirectoryAction, CommandAction
from craftr.core.actions.action import Action
from craftr.core.configurable import Closure


class HaskellApplication(Task):

  srcs: te.Annotated[Property[t.List[str]], Task.InputFile]
  compiler_flags: Property[t.List[str]]

  # Properties that construct the output filename.
  output_directory: Property[str]
  product_name: Property[str]
  suffix: Property[str]
  output_file: te.Annotated[Property[str], Task.Output]

  def init(self) -> None:
    self.output_directory.set_default(lambda: os.path.join(self.project.build_directory, 'haskell', self.name))
    self.product_name.set_default(lambda: 'main')
    self.suffix.set_default(lambda: '.exe' if os.name == 'nt' else '')
    self.output_file.set_default(lambda: os.path.join(self.output_directory.get(), self.product_name.get() + self.suffix.get()))
    self.run = self.project.task(self.name + 'Run')
    self.run.group = 'run'
    self.run.default = False
    self.run.always_outdated = True
    self.run.depends_on(self)

  def finalize(self) -> None:
    super().finalize()
    self.run.do_last(CommandAction([self.output_file.get()]))

  def get_actions(self) -> t.List['Action']:
    output_file = self.output_file.get()
    srcs = self.srcs.get()
    command = ['ghc', '-o', output_file] + srcs + self.compiler_flags.or_else([])

    actions: t.List[Action] = [
      CreateDirectoryAction(os.path.dirname(output_file)),
      CommandAction(command),
    ]

    # TODO(nrosenstein): Add cleanup action to remove .hi/.o files?
    #   There doesn't seem to be an option in the Ocaml compiler to change their
    #   output location.

    return actions


def apply(project: Project, name: str) -> None:
  project.add_extension('HaskellApplication', HaskellApplication)
  project.add_extension('haskellApplication', TaskFactoryExtension(project, 'haskellApplication', HaskellApplication))

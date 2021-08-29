
"""
Provides a simple interface to building OCaml applications.
"""

import os
import typing as t
import typing_extensions as te

from craftr.core import Project, Property, Task, Namespace
from craftr.core.actions import CreateDirectoryAction, CommandAction
from craftr.core.actions.action import Action


class OcamlApplicationTask(Task):

  output_file: te.Annotated[Property[str], Task.Output]
  srcs: te.Annotated[Property[t.List[str]], Task.InputFile]
  standalone: Property[bool]

  # Properties that construct the output filename.
  output_directory: Property[str]
  product_name: Property[str]
  suffix: Property[str]

  def init(self) -> None:
    self.standalone.set_default(lambda: False)
    self.output_directory.set_default(lambda: os.path.join(self.project.build_directory, 'ocaml', self.name))
    self.product_name.set_default(lambda: 'main')
    self.suffix.set_default(lambda: '.exe' if (self.standalone.get() and os.name == 'nt') else '' if self.standalone.get() else '.cma')
    self.output_file.set_default(lambda: os.path.join(self.output_directory.get(), self.product_name.get() + self.suffix.get()))

    self.run = self.project.task(self.name + 'Run')
    self.run.group = 'run'
    self.run.default = False
    self.run.depends_on(self)

  def finalize(self) -> None:
    super().finalize()
    self.run.do_last(CommandAction([self.output_file.get()]))

  def get_actions(self) -> t.List['Action']:
    command = ['ocamlopt' if self.standalone.get() else 'ocamlc']
    command += ['-o'] + [self.output_file.get()] + self.srcs.get()

    # TODO(nrosenstein): Add cleanup action to remove .cmi/cmx/.o files?
    #   There doesn't seem to be an option in the Ocaml compiler to change their
    #   output location.

    return [
      CreateDirectoryAction(os.path.dirname(self.output_file.get())),
      CommandAction(command),
    ]


def apply(project: Project, namespace: Namespace) -> None:
  namespace.add('OcamlApplicationTask', OcamlApplicationTask)
  namespace.add_task_factory('ocamlApplication', OcamlApplicationTask)

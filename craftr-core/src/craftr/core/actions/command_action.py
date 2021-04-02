
import shlex
import subprocess as sp
import typing as t
from dataclasses import dataclass

from craftr.core.actions.action import Action
from craftr.core.system.task import Task
from craftr.core.types import File


@dataclass
class CommandAction(Action):

  #: A command line to execute.
  command: t.Optional[t.List[t.Union[str, File]]] = None

  #: A list of command lines to execute in order. If both #command and #commands are
  #: specified, #command is executed first.
  commands: t.Optional[t.List[t.List[t.Union[str, File]]]] = None

  #: The working directory in which to execute the command(s).
  working_directory: t.Optional[File] = None

  #: If this is enabled, the command that is being run is printed to stdout.
  verbose: bool = False

  def format_command(self, command: t.List[str]) -> str:
    return '$ ' + ' '.join(map(shlex.quote, command))

  def execute(self) -> None:
    commands: t.List[t.List[str]] = []
    if self.command is not None:
      commands.append([str(x) for x in self.command])
    if self.commands is not None:
      commands.extend([[str(x) for x in cmd] for cmd in self.commands])
    for command in commands:
      if self.verbose:
        print(self.format_command(command))
      sp.check_call(command, cwd=self.working_directory)

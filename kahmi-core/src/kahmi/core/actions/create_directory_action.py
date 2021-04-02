
import os
from dataclasses import dataclass

from kahmi.core.actions.action import Action
from kahmi.core.system.task import Task
from kahmi.core.types import File


@dataclass
class CreateDirectoryAction(Action):

  #: The path of the directory to create.
  path: File

  def execute(self) -> None:
    if not os.path.isdir(self.path):
      os.makedirs(self.path, exist_ok=True)

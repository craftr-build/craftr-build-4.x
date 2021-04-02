
import os
from dataclasses import dataclass

from craftr.core.actions.action import Action
from craftr.core.system.task import Task
from craftr.core.types import File


@dataclass
class CreateDirectoryAction(Action):

  #: The path of the directory to create.
  path: File

  def execute(self) -> None:
    if not os.path.isdir(self.path):
      os.makedirs(self.path, exist_ok=True)

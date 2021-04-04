
import os
from dataclasses import dataclass

from craftr.core.types import File
from .action import Action, ActionContext


@dataclass
class CreateDirectoryAction(Action):

  #: The path of the directory to create.
  path: File

  def execute(self, context: ActionContext) -> None:
    if not os.path.isdir(self.path):
      os.makedirs(self.path, exist_ok=True)

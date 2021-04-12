
import os
from dataclasses import dataclass
from pathlib import Path

from .action import Action, ActionContext


@dataclass
class CreateDirectoryAction(Action):

  #: The path of the directory to create.
  path: Path

  def execute(self, context: ActionContext) -> None:
    if not os.path.isdir(self.path):
      os.makedirs(self.path, exist_ok=True)

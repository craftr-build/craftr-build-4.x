
import typing as t
from dataclasses import dataclass
from .action import Action, ActionContext


@dataclass
class LambdaAction(Action):

  delegate: t.Callable[[ActionContext], None]

  def execute(self, context: ActionContext) -> None:
    self.delegate(context)

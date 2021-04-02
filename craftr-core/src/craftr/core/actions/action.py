
import abc
import typing as t

from craftr.core.property import Property
from craftr.core.property.provider import NoValueError
from craftr.core.system.task import Task

if t.TYPE_CHECKING:
  from craftr.core.system.project import Project


class Action(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def execute(self) -> None:
    pass

  @classmethod
  def as_task(cls, project: 'Project', name: str) -> 'Task':
    """
    Factory function to produce a task that contains exactly the properties of this action through
    the class annotations. The action will be created by passing a keyword argument for every
    populated property value.
    """

    class ActionAsTask(Task):
      __annotations__ = {k: Property[v] for k, v in t.get_type_hints(cls).items()}  # type: ignore

      def get_actions(self) -> t.List[Action]:
        kwargs: t.Dict[str, t.Any] = {}
        for key, prop in self.get_properties().items():
          try:
            kwargs[key] = prop.get()
          except NoValueError:
            if hasattr(cls, key):
              kwargs[key] = getattr(cls, key)
            else:
              raise
        return [cls(**kwargs)]

    ActionAsTask.__name__ = cls.__name__ + 'AsTask'
    ActionAsTask.__qualname__ = ActionAsTask.__qualname__.rpartition('.')[0] \
        + '.' + ActionAsTask.__name__
    return ActionAsTask(project, name)

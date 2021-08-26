
import abc
import typing as t
from dataclasses import dataclass

if t.TYPE_CHECKING:
  from craftr.core.project import Project


@dataclass
class PluginNotFoundError(Exception):
  loader: t.Optional['IPluginLoader']
  plugin_name : str

  def __str__(self) -> str:
    return f'Plugin "{self.plugin_name}" could not be found' + (
        f' by loader `{self.loader}`' if self.loader else '')


@t.runtime_checkable
class IPlugin(t.Protocol, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def apply(self, project: 'Project', name: str) -> t.Any:
    """
    Apply the plugin to the given project.
    """


@t.runtime_checkable
class IPluginLoader(t.Protocol, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def load_plugin(self, plugin_name: str) -> IPlugin:
    """
    Load the given plugin by name.
    """

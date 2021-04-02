
import pkg_resources
import typing as t
from dataclasses import dataclass

from craftr.core.system.settings import Settings

if t.TYPE_CHECKING:
  from craftr.core.system.project import Project


@dataclass
class PluginNotFoundError(Exception):
  loader: t.Optional['IPluginLoader']
  plugin_name : str

  def __str__(self) -> str:
    return f'Plugin "{self.plugin_name}" could not be found' + (
        f' by loader `{self.loader}`' if self.loader else '')


@t.runtime_checkable
class IPlugin(t.Protocol):

  def apply(self, project: 'Project') -> None:
    """
    Apply the plugin to the given project.
    """


@t.runtime_checkable
class IPluginLoader(t.Protocol):

  def load_plugin(self, plugin_name: str) -> IPlugin:
    """
    Load the given plugin by name.
    """


@dataclass
class DefaultPluginLoader(IPluginLoader):
  """
  Default implementation for loading plugins via the `craftr.plugins` entrypoint.
  """

  entrypoint_name: str = 'craftr.plugins'

  @classmethod
  def from_settings(cls, settings: Settings) -> None:
    return cls(settings.get('craftr.core.system.plugin.DefaultPluginLoader', cls.entrypoint_name))

  def load_plugin(self, plugin_name: str) -> IPlugin:
    for ep in pkg_resources.iter_entry_points(self.entrypoint_name, plugin_name):
      return ep.load()
    raise PluginNotFoundError(self, plugin_name)


import pkg_resources
from dataclasses import dataclass

from craftr.core.settings import Settings
from .api import IPluginLoader, IPlugin, PluginNotFoundError


@dataclass
class DefaultPluginLoader(IPluginLoader):
  """
  Default implementation for loading plugins via the `craftr.plugins` entrypoint.
  """

  entrypoint_name: str = 'craftr.plugins'

  @classmethod
  def from_settings(cls, settings: Settings) -> 'DefaultPluginLoader':
    return cls(settings.get('craftr.core.system.plugin.DefaultPluginLoader', cls.entrypoint_name))

  def load_plugin(self, plugin_name: str) -> IPlugin:
    for ep in pkg_resources.iter_entry_points(self.entrypoint_name, plugin_name):
      value = ep.load()
      if not isinstance(value, IPlugin):
        raise RuntimeError(f'Plugin "{plugin_name}" loaded by `{self}` does not implement the '
            'IPlugin protocol.')
      return value
    raise PluginNotFoundError(self, plugin_name)

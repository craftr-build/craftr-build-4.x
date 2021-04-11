
"""
Provides the extensions that are always available in a project.
"""

from craftr.build.lib import PluginRegistration
from .run import RunTask

plugin = PluginRegistration()
plugin.exports(RunTask)
apply = plugin.apply

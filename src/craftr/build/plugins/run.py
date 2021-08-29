
import typing as t
from craftr.core.plugin.api import Namespace

from craftr.core.project.project import Project

from craftr.build.lib import ExecutableInfo, IExecutableProvider
from craftr.build.lib.helpers import PluginRegistration
from craftr.core.actions import Action, CommandAction
from craftr.core.property import Property
from craftr.core.task import Task


class RunTask(Task):

  executable: Property[t.Union[IExecutableProvider, ExecutableInfo, str]]

  def init(self) -> None:
    self.default = False
    self.always_outdated = True

  def get_actions(self) -> t.List[Action]:
    executable = self.executable.or_else(None)
    if isinstance(executable, str):
      executable = ExecutableInfo(executable)
    elif isinstance(executable, IExecutableProvider):
      executable = executable.get_executable_info()
    elif not executable:
      dependencies = self.get_dependencies()
      if not dependencies:
        raise RuntimeError(f'No dependencies in RunTask')
      providers = t.cast(t.List[IExecutableProvider], list(filter(lambda t: isinstance(t, IExecutableProvider), dependencies)))
      if not providers:
        raise RuntimeError(f'No IExecutableProvider in RunTask dependencies')
      if len(providers) > 1:
        raise RuntimeError(f'Multiple IExecutableProvider in RunTask dependencies')
      executable = providers[0].get_executable_info()

    assert isinstance(executable, ExecutableInfo)
    return [CommandAction(executable.invokation_layout or [executable.filename])]


def apply(project: Project, namespace: Namespace) -> None:
  namespace.add_task_factory('run', RunTask)

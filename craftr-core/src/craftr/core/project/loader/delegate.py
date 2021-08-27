
import logging
import typing as t
from pathlib import Path

from craftr.core.settings import IHasFromSettings, Settings
from .api import CannotLoadProject, IProjectLoader

if t.TYPE_CHECKING:
  from craftr.core.context import Context
  from craftr.core.project import Project


class DelegateProjectLoader(IProjectLoader, IHasFromSettings):
  """
  Delegates the project loading process to a sequence of other loaders. Returns the first project
  loaded by any loader.

  If created from configuration, the `craftr.plugin.loader.delegates` option is respected, which
  must be a comma-separated list of fully qualified lodaer names. A loader name may be trailed by
  a question mark to ignore if the loader name cannot be resolved.
  """

  log = logging.getLogger(__qualname__ + '.' + __name__)  # type: ignore

  DEFAULT_DELEGATES = 'craftr.core.project.loader.default.DefaultProjectLoader,craftr.build.loader.DslProjectLoader?'

  def __init__(self, delegates: t.List[IProjectLoader]) -> None:
    self.delegates = delegates

  @classmethod
  def from_settings(cls, settings: 'Settings') -> 'DelegateProjectLoader':
    delegates: t.List[IProjectLoader] = []
    names = settings.get('core.plugin.loader.delegates', cls.DEFAULT_DELEGATES).split(',')
    for name in map(str.strip, names):
      ignore_unresolved = bool(name.endswith('?') and name[:-1])
      try:
        delegates.append(settings.create_instance(IProjectLoader, name))  # type: ignore
      except ImportError as exc:
        if ignore_unresolved:
          cls.log.warn('unable to resolve delegate project loader "%s"', name)
        else:
          raise
    return cls(delegates)

  def load_project(self, context: 'Context', parent: t.Optional['Project'], path: Path) -> 'Project':
    for delegate in self.delegates:
      try:
        return delegate.load_project(context, parent, path)
      except CannotLoadProject:
        pass
    raise CannotLoadProject(self, context, parent, path)

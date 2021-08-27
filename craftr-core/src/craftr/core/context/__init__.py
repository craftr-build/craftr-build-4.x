
import typing as t
from pathlib import Path

from nr.caching.api import NamespaceStore

from craftr.core.executor import IExecutor, ExecutionGraph
from craftr.core.plugin import IPluginLoader
from craftr.core.project import IProjectLoader, Project
from craftr.core.settings import Settings
from craftr.core.task import Task, ITaskSelector
from craftr.core.util.caching import JsonDirectoryStore
from craftr.core.util.preconditions import check_not_none


class Context:
  """
  The context carries globally accessible data for a craftr build. If not *settings* are specified,
  the `craftr.properties` file is read from the current working directory (if it exists).

  # Supported Settings

  * `core.build_directory` (no default)
  * `core.executor` (defaults to `craftr.core.executor.simple.SimpleExecutor`)
  * `core.task_selector` (defaults to `craftr.core.task.selector.default.DefaultTaskSelector`)
  """

  DEFAULT_EXECUTOR = 'craftr.core.executor.default.DefaultExecutor'
  DEFAULT_PLUGIN_LOADER = 'craftr.core.plugin.default.DefaultPluginLoader'
  DEFAULT_SELECTOR = 'craftr.core.task.selector.default.DefaultTaskSelector'
  DEFAULT_PROJECT_LOADER = 'craftr.core.project.loader.delegate.DelegateProjectLoader'
  CRAFTR_SETTINGS_FILE = Path('build.settings')

  def __init__(
    self, *,
    settings: t.Optional[Settings] = None,
    executor: t.Optional[IExecutor] = None,
    plugin_loader: t.Optional[IPluginLoader] = None,
    project_loader: t.Optional[IProjectLoader] = None,
  ) -> None:

    if settings is None and self.CRAFTR_SETTINGS_FILE.exists():
      settings = Settings.parse(self.CRAFTR_SETTINGS_FILE.read_text().splitlines())
    elif settings is None:
      settings = Settings.of({})

    self._root_project: t.Optional[Project] = None
    self.settings = settings
    self.executor = executor or settings.get_instance(
        IExecutor, 'core.executor', self.DEFAULT_EXECUTOR)  # type: ignore
    self.plugin_loader = plugin_loader or settings.get_instance(
        IPluginLoader, 'core.plugin.loader', self.DEFAULT_PLUGIN_LOADER)  # type: ignore
    self.project_loader = project_loader or settings.get_instance(
        IProjectLoader, 'core.project.loader', self.DEFAULT_PROJECT_LOADER)  # type: ignore
    self.task_selector = self.settings.get_instance(
        ITaskSelector, 'core.task_selector', self.DEFAULT_SELECTOR)  # type: ignore
    self.graph = ExecutionGraph()
    self._metadata_store: t.Optional[NamespaceStore] = None

  @property
  def metadata_store(self) -> NamespaceStore:
    if self._metadata_store is None:
      self._metadata_store = JsonDirectoryStore(
        str(self.get_default_build_directory(self.root_project) / '.craftr-metadata'), create_dir=True)
    return self._metadata_store

  @property
  def root_project(self) -> t.Optional[Project]:
    return self._root_project

  def load_project(self, path: Path) -> Project:
    """
    Initialize the root project and return it.
    """

    project = self.project_loader.load_project(self, None, path)
    self._root_project = project
    return project

  def initialize_project(self, project: Project) -> None:
    """
    Called when a project is created. Can be overwritten by subclasses to customize what happens
    when a project is created. The default implementationa applies the "default" plugin.
    """

    pass

  def get_default_build_directory(self, project: Project) -> Path:
    """
    Returns the default build directory for a project, used if no explicit build directory is
    set. The default implementation returns the `.build/` directory in the project's directory,
    unless `core.build_directory` is set.
    """

    build_directory = self.settings.get('core.build_directory', None)
    if build_directory is None:
      return project.directory.joinpath('.build')
    else:
      return Path(build_directory)

  def finalize(self) -> None:
    self.root_project.finalize()

  def execute(self, selection: t.Union[None, str, t.List[str], Task, t.List[Task]] = None) -> None:
    root_project = check_not_none(self.root_project, 'no root project initialized')
    selected_tasks: t.Set[Task] = set()

    if selection is None:
      selected_tasks.update(self.task_selector.select_default(root_project))
    else:
      if isinstance(selection, (str, Task)):
        selection = t.cast(t.Union[t.List[str], t.List[Task]], [selection])
      for item in selection:
        if isinstance(item, Task):
          selected_tasks.add(item)
        elif isinstance(item, str):
          result_set = self.task_selector.select_tasks(item, root_project)
          if not result_set:
            raise ValueError(f'selector matched no tasks: {item!r}')
          selected_tasks.update(result_set)
        else:
          raise TypeError(f'expected str|Task, got {type(item).__name__}')

    self.graph.add_tasks(selected_tasks)
    self.graph.ready()
    self.executor.execute(self.graph)

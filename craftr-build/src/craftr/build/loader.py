
import typing as t
from pathlib import Path
from craftr.dsl import transpile_to_ast
from craftr.core.context import Context
from craftr.core.project import CannotLoadProject, IProjectLoader, Project
from craftr.core.closure import closure

BUILD_SCRIPT_FILENAME = 'build.craftr'


class DslProjectLoader(IProjectLoader):

  def load_project(self, context: Context, parent: t.Optional[Project], path: Path) -> Project:
    if (filename := path / BUILD_SCRIPT_FILENAME).exists():
      project = Project(context, parent, path)
      context.initialize_project(project)
      @closure(project)
      def _execute(__closure__):
        module = transpile_to_ast(filename.read_text(), str(filename))
        scope = {'project': project, '__file__': str(filename), '__name__': project.name, '__closure__': __closure__}
        exec(compile(module, str(filename), 'exec'), scope, scope)
      _execute()
      return project
    raise CannotLoadProject(self, context, parent, path)


import typing as t
from pathlib import Path
from craftr.dsl import execute, transpile_to_ast
from craftr.core.context import Context
from craftr.core.project import CannotLoadProject, IProjectLoader, Project

BUILD_SCRIPT_FILENAME = 'build.craftr'


class DslProjectLoader(IProjectLoader):

  def load_project(self, context: Context, parent: t.Optional[Project], path: Path) -> Project:
    if (filename := path / BUILD_SCRIPT_FILENAME).exists():
      project = Project(context, parent, path)
      context.initialize_project(project)
      project.ext.add('__file__', str(filename))
      project.ext.add('__name__', project.name)
      execute(filename.read_text(), str(filename), project.ext.__attrs__)
      return project

    raise CannotLoadProject(self, context, parent, path)

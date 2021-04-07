
import enum
import typing as t
from pathlib import Path

from craftr.dsl import execute_file
from craftr.core.error import BuildError
from .api import IProjectLoader
from ..project import Project

if t.TYPE_CHECKING:
  from craftr.core.context import Context


class BuildScriptType(enum.Enum):
  CRAFTR = Path('build.craftr')
  PYTHON = Path('build.craftr.py')


class DefaultProjectLoader(IProjectLoader):

  def load_project(self, context: 'Context', parent: t.Optional[Project], path: Path) -> Project:
    project = Project(context, parent, path)
    context.initialize_project(project)
    if (filename := path / BuildScriptType.CRAFTR.value).exists():
      execute_file(filename, project)
    elif (filename := path / BuildScriptType.PYTHON.value).exists():
      scope = {'project': project, '__file__': str(filename), '__name__': '__main__'}
      exec(compile(filename.read_text(), str(filename), 'exec'), scope, scope)
    else:
      raise BuildError('No build file found in current directory.')
    return project

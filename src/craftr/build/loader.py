
import typing as t
from pathlib import Path
from craftr.dsl.runtime import ChainContext, Context, Closure, DefaultContext
from craftr.core.context import Context
from craftr.core.project import CannotLoadProject, IProjectLoader, Project

BUILD_SCRIPT_FILENAME = 'build.craftr'


def context_factory(obj: t.Any) -> Context:
  if isinstance(obj, Project):
    return ChainContext(DefaultContext(obj), DefaultContext(obj.ext))
  else:
    return DefaultContext(obj)


class DslProjectLoader(IProjectLoader):

  def load_project(self, context: Context, parent: t.Optional[Project], path: Path) -> Project:
    if (filename := path / BUILD_SCRIPT_FILENAME).exists():
      project = Project(context, parent, path)
      context.initialize_project(project)
      project.ext.add('__file__', str(filename))
      project.ext.add('__name__', project.name)
      Closure(None, None, project, context_factory).run_code(filename.read_text(), str(filename))
      return project

    raise CannotLoadProject(self, context, parent, path)

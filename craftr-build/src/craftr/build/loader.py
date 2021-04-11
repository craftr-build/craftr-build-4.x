
class DslProjectLoader(IProjectLoader):

  def load_project(self, context: 'Context', parent: t.Optional[Project], path: Path) -> Project:
    if (filename := path / BUILD_SCRIPT_FILENAME).exists():
      project = Project(context, parent, path)
      context.initialize_project(project)
      scope = {'project': project, '__file__': str(filename), '__name__': '__main__'}
      exec(compile(filename.read_text(), str(filename), 'exec'), scope, scope)
      return project
    raise CannotLoadProject(self, context, parent, path)

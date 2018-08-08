
import nodepy


class CraftrModule(nodepy.loader.PythonModule):

  def __init__(self, session, *args, is_main=False, **kwargs):
    super().__init__(*args, **kwargs)
    self.is_main = is_main
    self.session = session

  def _exec_code(self, code):
    assert self.loaded
    assert isinstance(code, str), type(code)
    with self.session.enter_scope(None, None, str(self.directory)):
      super()._exec_code(code)


class CraftrModuleLoader(nodepy.resolver.StdResolver.Loader):

  def __init__(self, session):
    self.session = session

  def suggest_files(self, context, path):
    if path.suffix == '.craftr':
      yield path
      path = path.with_suffix('')
    else:
      yield path.with_suffix('.craftr')
    path = nodepy.resolver.resolve_link(context, path)
    yield path.joinpath('build.craftr')

  def can_load(self, context, path):
    return path.suffix == '.craftr'

  def load_module(self, context, package, filename):
    return CraftrModule(self.session, context, None, filename)

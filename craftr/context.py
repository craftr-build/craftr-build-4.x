
import collections
import json
from . import core, dsl, path, props


class Context(dsl.BaseDslContext):

  def __init__(self, build_directory, build_mode='debug', backend_name=None):
    self.path = ['.', path.join(path.dir(__file__), 'lib')]
    self.options = {}
    self.modules = {}
    self.build_directory = build_directory
    self.build_mode = build_mode
    self.backend_name = backend_name or 'backends.ninja'

    self.builtins = props.Namespace('builtins')
    self.builtins.context = self
    self.load_file(path.join(path.dir(__file__), 'builtins.py'), self.builtins)

    self.build_graph = core.BuildGraph()

  def translate_targets(self, module):
    for module in self.modules.values():
      for handler in module.target_handlers():
        handler.translate_begin()
    seen = set()
    def translate(target):
      for dep in target.dependencies():
        if dep.target():
          translate(dep.target())
        else:
          for other_target in dep.module().targets():
            translate(other_target)
      if target not in seen:
        seen.add(target)
        for handler in target.target_handlers():
          handler.translate_target(target, target.handler_data(handler))
    for target in module.targets():
      translate(target)
    for module in self.modules.values():
      for handler in module.target_handlers():
        handler.translate_end()
      for target in module.targets():
        self.build_graph.add_actions(target.actions())

  def load_module_file(self, filename, is_main=False):
    with open(filename) as fp:
      project = dsl.Parser().parse(fp.read(), filename)
    if project.name in self.modules:
      raise RuntimeError('modules {!r} already loaded'.format(project.name))
    module = dsl.Interpreter(self, filename, is_main)(project)
    self.modules[module.name()] = module
    return module

  def to_json(self):
    root = collections.OrderedDict()
    root['path'] = self.path
    root['backend'] = self.backend_name
    root['mode'] = self.build_mode
    root['directory'] = self.build_directory
    root['options'] = None  # TODO: Include options specified via the command-line.
    root['graph'] = self.build_graph.to_json()
    return root

  def from_json(self, root):
    self.path = root['path']
    self.backend_name = root['backend']
    self.build_mode = root['mode']
    if self.build_directory != root['directory']:
      print('warning: stored build directory does not match current build directory')
    # TODO: Read options
    self.build_graph.from_json(root['graph'])

  def serialize(self):
    path.makedirs(self.build_directory)
    with open(path.join(self.build_directory, 'CraftrBuildGraph.json'), 'w') as fp:
      json.dump(self.to_json(), fp)

  def deserialize(self):
    with open(path.join(self.build_directory, 'CraftrBuildGraph.json')) as fp:
      root = json.load(fp, object_pairs_hook=collections.OrderedDict)
    self.from_json(root)

  # dsl.Context

  def get_option(self, module_name, option_name):
    return self.options[module_name + '.' + option_name]

  def get_module(self, module_name):
    if module_name not in self.modules:
      for x in self.path:
        filename = path.join(x, module_name + '.craftr')
        if path.isfile(filename):
          break
        filename = path.join(x, module_name, 'build.craftr')
        if path.isfile(filename):
          break
      else:
        raise dsl.ModuleNotFoundError(module_name)
      with open(filename) as fp:
        project = dsl.Parser().parse(fp.read(), filename)
      module = dsl.Interpreter(self, filename)(project)
      self.modules[module_name] = module
    else:
      module = self.modules[module_name]
    return module

  def update_config(self, config):
    # TODO: Merge fields?
    self.options.update(config)

  def init_namespace(self, ns):
    super().init_namespace(ns)
    for key in self.builtins.__all__:
      setattr(ns, key, getattr(self.builtins, key))

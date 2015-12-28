# Copyright (C) 2015  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
''' Craftr is a powerful meta build system for Ninja. '''

__author__ = 'Niklas Rosenstein <rosensteinniklas(at)gmail.com>'
__version__ = '0.20.0-dev'

import sys
if sys.version < '3.4':
  raise EnvironmentError('craftr requires Python3.4')

from os import environ
from craftr import magic

session = magic.new_context('session')
module = magic.new_context('module')

import craftr
import collections
import os
import types
import warnings

# This object is used to indicate a state where a parameter was
# not specified. This is used when None would be an accepted value.
_sentinel = object()


class Session(object):
  ''' The `Session` object is the manage of a meta build session that
  manages the craftr modules and build `Target`s.

  Attributes:
    path: A list of additional search paths for Craftr modules.
    modules: A dictionary of craftr extension modules, without the
      `craftr.ext.` prefix.
    targets: A dictionary mapping full target names to actual `Target`
      objects that have been created. The `Target` constructors adds
      the object to this dictionary automatically.
    var: A dictionary of variables that will be exported to the Ninja
      build definitions file.
    verbosity: Logging verbosity level, defaults to 0.
    strace_depth: The maximum number of frames to print on a stack
      trace of a logging output with `info()`, `warn()` or `error()`.
      Defaults to 3.
    '''

  def __init__(self, cwd=None, path=None):
    super().__init__()
    self.cwd = cwd or os.getcwd()
    self.env = environ.copy()
    self.extension_importer = ext.CraftrImporter(self)
    self.path = [craftr.path.join(craftr.path.dirname(__file__), 'lib')]
    self.modules = {}
    self.targets = {}
    self.var = {}
    self.verbosity = 0
    self.strace_depth = 3

    if path is not None:
      self.path.extend(path)

  def exec_if_exists(self, filename):
    ''' Executes *filename* if it exists. Used for running the Craftr
    environment files before the modules are loaded. Returns None if the
    file does not exist, a `types.ModuleType` object if it was executed. '''

    if not os.path.isfile(filename):
      return None

    # Create a fake module so we can enter a module context
    # for the environment script.
    temp_mod = types.ModuleType('craftr.ext.__temp__:' + filename)
    temp_mod.__file__ = filename
    init_module(temp_mod)
    temp_mod.__name__ = '__craftenv__'

    with open(filename, 'r') as fp:
      code = compile(fp.read(), filename, 'exec')
    with magic.enter_context(module, temp_mod):
      exec(code, vars(module))

    return temp_mod

  def update(self):
    ''' See `extr.CraftrImporter.update()`. '''

    self.extension_importer.update()

  def on_context_enter(self, prev):
    if prev is not None:
      raise RuntimeError('session context can not be nested')

    # We can not change os.environ effectively, we must update the
    # dictionary instead.
    self._old_environ = environ.copy()
    environ.clear()
    environ.update(self.env)
    self.env = environ

    sys.meta_path.append(self.extension_importer)
    self.update()

  def on_context_leave(self):
    ''' Remove all `craftr.ext.` modules from `sys.modules` and make
    sure they're all in `Session.modules` (the modules are expected
    to be put there by the `craftr.ext.CraftrImporter`). '''

    # Restore the original values of os.environ.
    self.env = environ.copy()
    environ.clear()
    environ.update(self._old_environ)
    del self._old_environ

    sys.meta_path.remove(self.extension_importer)
    for key, module in list(sys.modules.items()):
      if key.startswith('craftr.ext.'):
        name = key[11:]
        assert name in self.modules and self.modules[name] is module, key
        del sys.modules[key]
        try:
          # Remove the module from the `craftr.ext` modules contents, too.
          delattr(ext, name.split('.')[0])
        except AttributeError:
          pass


class Target(object):
  ''' This class is a direct representation of a Ninja rule and the
  corresponding in- and output files that will be built using that rule.

  Attributes:
    name: The name of the target. This is usually deduced from the
      variable the target is assigned to if no explicit name was
      passed to the `Target` constructor. Note that the actualy
      identifier of the target that can be passed to Ninja is
      concatenated with the `module` identifier.
    module: A Craftr extension module which this target belongs to. It
      can be specified on construction manually, or the current active
      module is used automatically.
    command: A list of strings that represents the command to execute.
    inputs: A list of filenames that are listed as direct inputs.
    outputs: A list of filenames that are generated by the target.
    implicit_deps: A list of filenames that mark the target as dirty
      if they changed and will cause it to be rebuilt, but that are
      not taken as direct input files (i.e. `$in` does not expand these
      files).
    order_only_deps: See "Order-only dependencies" in the [Ninja Manual][].
    foreach: A boolean value that determines if the command is appliead
      for each pair of filenames in `inputs` and `outputs`, or invoked
      only once. Note that if this is True, the number of elements in
      `inputs` and `outputs` must match!
    description: A description of the target to display when it is being
      built. This ends up as a variable definition to the target's rule,
      so you may use variables in this as well.
    pool: The name of the build pool. Defaults to None. Can be "console"
      for "targets" that don't actually build files but run a program.
      Craftr ensures that targets in the "console" pool are never
      executed implicitly when running Ninja.  # xxx: todo!
    deps: The mode for automatic dependency detection for C/C++ targets.
      See the "C/C++ Header Depenencies" section in the [Ninja Manual][].
    depfile: A filename that contains additional dependencies.
    msvc_deps_prefix: The MSVC dependencies prefix to be used for the rule.
    explicit: If True, the target will only be built by Ninja if it is
      explicitly targeted from the command-line or required by another
      target. Defaults to False.

  [Ninja Manual]: https://ninja-build.org/manual.html
  '''

  def __init__(self, command, inputs=None, outputs=None, implicit_deps=None,
      order_only_deps=None, foreach=False, description=None, pool=None,
      var=None, deps=None, depfile=None, msvc_deps_prefix=None,
      explicit=False, frameworks=None, module=None, name=None):

    if not module:
      module = craftr.module()
    if not name:
      name = Target._get_name(module)

    if isinstance(command, str):
      command = shell.split(command)
    else:
      command = _check_list_of_str('command', command)
    if not command:
      raise ValueError('command can not be empty')

    if inputs is not None:
      if isinstance(inputs, str):
        inputs = [inputs]
      inputs = expand_inputs(inputs)
      inputs = _check_list_of_str('inputs', inputs)
    if outputs is not None:
      if isinstance(outputs, str):
        outputs = [outputs]
      elif callable(outputs):
        outputs = outputs(inputs)
      outputs = _check_list_of_str('outputs', outputs)

    if foreach and len(inputs) != len(outputs):
      raise ValueError('len(inputs) must match len(outputs) in foreach Target')

    if implicit_deps is not None:
      implicit_deps = _check_list_of_str('implicit_deps', implicit_deps)
    if order_only_deps is not None:
      order_only_deps = _check_list_of_str('order_only_deps', order_only_deps)

    self.module = module
    self.name = name
    self.command = command
    self.inputs = inputs
    self.outputs = outputs
    self.implicit_deps = implicit_deps or []
    self.order_only_deps = order_only_deps or []
    self.foreach = foreach
    self.pool = pool
    self.description = description
    self.deps = deps
    self.depfile = depfile
    self.msvc_deps_prefix = msvc_deps_prefix
    self.frameworks = frameworks or []
    self.explicit = explicit

    targets = module.__session__.targets
    if self.fullname in targets:
      raise ValueError('target {0!r} already exists'.format(self.fullname))
    targets[self.fullname] = self

  def __repr__(self):
    pool = ' in "{0}"'.format(self.pool) if self.pool else ''
    command = ' running "{0}"'.format(self.command[0])
    return '<Target {self.fullname!r}{command}{pool}>'.format(**locals())

  @staticmethod
  def _get_name(module):
    # Always use the frame of the current module, though.
    if craftr.module() != module:
      raise RuntimeError('target name deduction only available when '
        'used from the currently executed module')
    return magic.get_assigned_name(magic.get_module_frame(module))

  @property
  def fullname(self):
    return self.module.project_name + '.' + self.name


class TargetBuilder(object):
  ''' This is a helper class to make it easy to implement rule functions
  that create a `Target`. Rule functions usually depend on inputs (being
  files or other `Target`s that can also bring additional frameworks),
  rule-level settings and frameworks. The `TargetBuilder` takes all of
  this into account and prepares the data conveniently. '''

  def __init__(self, inputs, frameworks, kwargs, module=None, name=None, stacklevel=1):
    self.caller = magic.get_caller_human(stacklevel + 1)
    frameworks = list(frameworks)
    self.inputs = expand_inputs(inputs, frameworks)
    self.frameworks = frameworks
    self.options = FrameworkJoin(Framework(self.caller, kwargs), *frameworks)
    self.module = module or craftr.module()
    self.name = name
    self.target = {}
    if not self.name:
      try:
        self.name = Target._get_name(self.module)
      except ValueError:
        index = 0
        while True:
          name = '{0}_{1:0>4}'.format(self.caller, index)
          if name not in session.targets:
            break
          index += 1
        self.name = name

  @property
  def fullname(self):
    return self.module.project_name + '.' + self.name

  def __getitem__(self, key):
    return self.options[key]

  def get(self, key, default=None):
    return self.options.get(key, default)

  def merge(self, key):
    return self.options.get_merge(key)

  def warn(self, *objects, sep=' ', stacklevel=1, warntype=RuntimeWarning):
    message = sep.join(map(str, objects))
    message = 'Target({0!r}): {1}'.format(self.fullname, message)
    warnings.warn(message, warntype, stacklevel + 1)

  def invalid_option(self, option_name, option_value=_sentinel, cause=None):
    if option_value is _sentinel:
      option_value = self[option_name]
    message = 'invalid option: {0} = {1!r}'.format(option_name, option_value)
    if cause:
      message = '{0} ({1})'.format(message, cause)
    self.warn(message, stacklevel=2)

  def add_framework(self, __fw_or_name, __fw_dict=None, **kwargs):
    if not isinstance(__fw_or_name, Framework):
      fw = Framework(__fw_or_name, __fw_dict, **kwargs)
    else:
      fw = __fw_or_name
    if fw not in self.frameworks:
      self.frameworks.append(fw)
    self.options += [fw]
    return fw

  def expand_inputs(self, inputs):
    frameworks = []
    result = expand_inputs(inputs, frameworks)
    self.frameworks += frameworks
    self.options += frameworks
    return result

  def create_target(self, command, inputs=None, outputs=None, **kwargs):
    if inputs is None:
      inputs = self.inputs
    kwargs.setdefault('frameworks', self.frameworks)
    target = Target(command=command, inputs=inputs, outputs=outputs,
      module=self.module, name=self.name, **kwargs)
    for key, value in self.target.items():
      # We can only set attributes that the target already has.
      getattr(target, key)
      setattr(target, key, value)
    return target


class Framework(dict):
  ''' A framework rerpresentation a set of options that are to be taken
  into account by compiler classes. Eg. you might create a framework
  that contains the additional information and options required to
  compile code using OpenCL and pass that to the compiler interface.

  Compiler interfaces may also add items to `Target.frameworks`
  that can be taken into account by other target rules. `expand_inputs()`
  returns a list of frameworks that are being used in the inputs.

  Use the `Framework.Join` class to create an object to process the
  data from multiple frameworks. '''

  def __init__(self, __fw_name, __init_dict=None, **kwargs):
    super().__init__()
    if __init_dict is not None:
      self.update(__init_dict)
    self.update(kwargs)
    self.name = __fw_name

  def __repr__(self):
    return 'Framework(name={0!r}, {1})'.format(self.name, super().__repr__())


class FrameworkJoin(object):
  ''' This class is used to process a set of `Framework`s and retreive
  relevant information from it. For some options, you might want to read
  the first value that is specified in any of the frameworks, for another
  you may want to create a list of all values in the frameworks. This is
  what the `FrameworkJoin` allows you to do.

  ```python
  >>> fw1 = Framework('foo', defines=['DEBUG'])
  >>> fw2 = Framework('bar', defines=['DO_STUFF'])
  >>> FrameworkJoin(fw1, fw2).merge('defines')
  ['DEBUG', 'DO_STUFF']
  ```
  '''

  def __init__(self, *frameworks):
    super().__init__()
    self.used_keys = set()
    self.frameworks = []
    self += frameworks

  def __iadd__(self, frameworks):
    for fw in frameworks:
      if not isinstance(fw, Framework):
        raise TypeError('expected Framework, got {0}'.format(type(fw).__name__))
      if fw not in self.frameworks:
        self.frameworks.append(fw)
    return self

  def __getitem__(self, key):
    self.used_keys.add(key)
    for fw in self.frameworks:
      try:
        return fw[key]
      except KeyError:
        pass
    raise KeyError(key)

  def get(self, key, default=None):
    ''' Get the first available value of *key* from the frameworks. '''

    try:
      return self[key]
    except KeyError:
      return default

  def merge(self, key):
    ''' Merge all values of *key* in the frameworks into one list,
    assuming that every key is a non-string sequence and can be
    appended to a list. '''

    self.used_keys.add(key)
    result = []
    for fw in self.frameworks:
      try:
        value = fw[key]
      except KeyError:
        continue
      if not isinstance(value, collections.Sequence) or isinstance(value, str):
        raise TypeError('expected a non-string sequence for {0!r} '
          'in framework {1!r}, got {2}'.format(key, fw.name, type(value).__name__))
      result += value
    return result

  get_merge = merge  # Backwards compatibility


class ModuleError(RuntimeError):

  def __init__(self, module=None):
    self.module = module or craftr.module()


class ModuleReturn(Exception):
  pass


def return_():
  ''' Raise a `ModuleReturn` exception, causing the module execution
  to be aborted and returning back to the parent module. Note that this
  function can only be called from a Craftr modules global stack frame,
  otherwise a `RuntimeError` will be raised. '''

  if magic.get_frame(1).f_globals is not vars(module):
    raise RuntimeError('return_() can not be called outside the current '
      'modules global stack frame')
  raise ModuleReturn()


def expand_inputs(inputs, frameworks=None):
  ''' Expands a list of inputs into a list of filenames. An input is a
  string (filename) or a `Target` object from which the `Target.outputs`
  are used. Returns a list of strings.

  If *frameworks* is specified, it must be a `list` to which the
  frameworks of all input `Target`s will be appended. '''

  if frameworks is not None and not isinstance(frameworks, list):
    raise TypeError('frameworks must be None or list')

  result = []

  # We also accept a single string or Target as input.
  if isinstance(inputs, (str, Target)):
    inputs = [inputs]

  for item in inputs:
    if isinstance(item, Target):
      if frameworks is not None:
        frameworks += item.frameworks
      result += item.outputs
    elif isinstance(item, str):
      result.append(item)
    else:
      raise TypeError('input must be Target or str, got {0}'.format(type(item).__name__))

  return result


def import_file(filename):
  ''' Import a Craftr module by filename. '''

  if not path.isabs(filename):
    filename = path.local(filename)
  return session.extension_importer.import_file(filename)


def import_module(modname, globals=None, fromlist=None):
  ''' Similar to `importlib.import_module()`, but this function can
  also improt contents of *modname* into *globals*. If *globals* is
  specified, the module will be directly imported into the dictionary.
  If *fromlist* list `*`, a wildcard import into *globals* will be
  perfromed. *fromlist* can also be a list of names to import.

  This function always returns the root module. '''

  wildcard = False
  if fromlist == '*':
    wildcard = True
    fromlist = None

  root = module = __import__(modname, globals, fromlist=fromlist)
  for part in modname.split('.')[1:]:
    module = getattr(module, part)
  if globals is not None:
    if wildcard:
      if hasattr(module, '__all__'):
        for key in module.__all__:
          globals[key] = getattr(module, key)
      else:
        for key, value in vars(module).items():
          if not key.startswith('_'):
            globals[key] = value
    elif fromlist is not None:
      for key in fromlist:
        globals[key] = value
    else:
      globals[modname.partition('.')[0]] = root
  return root


def init_module(module):
  ''' Called when a craftr module is being imported before it is
  executed to initialize its contents. '''

  assert module.__name__.startswith('craftr.ext.')
  module.__session__ = session()
  module.project_dir = path.dirname(module.__file__)
  module.project_name = module.__name__[11:]


def finish_module(module):
  ''' Called when a craftr extension module was imported. This function
  makes sure that there is a `__all__` member on the module that excludes
  all the built-in names and that are not module objects. '''

  if not hasattr(module, '__all__'):
    module.__all__ = []
    for key in dir(module):
      if key.startswith('_') or key in ('project_dir', 'project_name'):
        continue
      if isinstance(getattr(module, key), types.ModuleType):
        continue
      module.__all__.append(key)


def _check_list_of_str(name, value):
  ''' Helper function to check if a given *value* is a list of strings
  or is convertible to a list of strings. Will raise a `ValueError` if
  not using the specified *name* as a hint. '''

  if not isinstance(value, str) and isinstance(value, collections.Iterable):
    value = list(value)
  if not isinstance(value, list):
    raise TypeError('expected list of str for {0}, got {1}'.format(
      name, type(value).__name__))
  for item in value:
    if not isinstance(item, str):
      raise TypeError('expected list of str for {0}, found {1} inside'.format(
        name, type(item).__name__))
  return value


from craftr import ext, path, shell, ninja
from craftr.logging import info, warn, error

__all__ = ['session', 'module', 'path', 'shell', 'environ',
  'Target', 'TargetBuilder', 'Framework', 'FrameworkJoin',
  'info', 'warn', 'error', 'return_', 'expand_inputs',
  'import_file', 'import_module']

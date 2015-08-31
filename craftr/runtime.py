# Copyright (C) 2015 Niklas Rosenstein
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

from craftr import utils, logging

import craftr
import os
import platform
import re
import sys

try:
  import colorama
except ImportError:
  colorama = None


class Session(object):
  ''' A session represents the state of the runtime that manages the
  execution of meta build scripts. The session initializes its module
  search path with the current working directory and the paths in the
  `CRAFTR_PATH` environment variable. '''

  class NamespaceProxy(utils.proxy.ProxyBase):
    __slots__ = ('_session', '_namespace')
    def __init__(self, session, namespace):
      super().__init__()
      self._session = session
      self._namespace = namespace
    def _get_current(self):
      return self._session.namespaces[self._namespace]

  def __init__(self, backend=None, outfile=None, logger=None):
    super().__init__()
    self.path = []
    self.path.append(os.getcwd())
    self.path.append(os.path.join(os.path.dirname(__file__), 'builtins'))
    self.path.extend(os.getenv('CRAFTR_PATH', '').split(os.path.sep))
    self.globals = utils.DataEntity('session_globals')
    self.modules = {}
    self.backend = craftr.backend.load_backend(backend)
    self.outfile = outfile or self.backend.default_outfile
    self.namespaces = {}
    self.logger = logging.Logger()
    self._mod_idcache = {}
    self._mod_filecache = {}
    self._init_globals()

  def _init_globals(self):
    self.globals.Platform = sys.platform
    self.globals.Arch = platform.architecture()[0]
    self.globals.Mach = platform.machine()

  def _register_module(self, module):
    ''' Register the specified *module* to the global module cache
    where only the loaded (not cached-only) modules lie and executes
    it if it hasn't been executed already. '''

    if module.executed:
      return

    prev = self.get_namespace(module.identifier)
    if prev.__entity_id__.startswith('ns:'):
      message = "resolving namespace entity '{0}' into module"
      for key, value in vars(prev).items():
        if not key.startswith('__'):
          setattr(module.locals, key, value)
    elif prev.__entity_id__.startswith('module:'):
      raise RuntimeError('module identifier already occupied', module.identifier)
    else:
      raise RuntimeError('unexpected entity name', prev.__entity_id__)

    self.modules[module.identifier] = module
    self.namespaces[module.identifier] = module.locals
    if not module.executed:
      self.logger.debug("executing module '{0}'".format(module.identifier))
      module.execute()

  def get_namespace(self, name):
    ''' Generate and retrieve the namespace under the specified *name*.
    Returned will be an `utils.proxy.LocalProxy` that references the
    namespace entry. '''

    if not utils.validate_ident(name):
      raise ValueError('invalid namespace identifier', name)
    parent = None
    parts = []
    for part in name.split('.'):
      # Generate the sub-namespace name.
      parts.append(part)
      name = '.'.join(parts)
      # Get or create the data entitiy for the namespace.
      try:
        entity = self.namespaces[name]
      except KeyError:
        entity = utils.DataEntity('ns:{0}'.format(name))
        self.namespaces[name] = entity
      proxy = Session.NamespaceProxy(self, name)
      # Make sure the parent has a reference to its sub-namespace.
      if parent:
        setattr(parent, part, proxy)
      parent = proxy

    return parent

  def get_module(self, name):
    ''' Returns a loaded module by its *name* or raises a `NoSuchModule`
    exception if there is no such module cached. '''

    try:
      return self.modules[name]
    except KeyError:
      raise NoSuchModule(name, None, 'get')

  def load_module(self, name, required_by=None, allow_reload=True):
    ''' Searches for a module in the `Session.path` list and all first-
    level subdirectories of the search path. Module filenames must be
    called `Craftr` or be suffixed with `.craftr`. A Module must contain
    a Craftr module declaration:

        # craftr_module(module_name)
    '''

    if not utils.validate_ident(name):
      raise ValueError('invalid module identifier', name)

    try:
      module = self._mod_idcache[name]
    except KeyError:
      pass
    else:
      self._register_module(module)
      return module

    if not allow_reload:
      raise NoSuchModule(name, required_by, 'load')

    for path in utils.path.iter_tree(self.path, depth=2):
      if not os.path.isfile(path):
        continue
      if os.path.basename(path) == 'Craftr' or path.endswith('.craftr'):
        try:
          self.load_module_file(path, register=False)
        except InvalidModule as exc:
          self.logger.warn(exc)

    return self.load_module(name, required_by, False)

  def load_module_file(self, filename, register=True):
    ''' Loads the `Module` from the specified *filename* and returns
    it. Raises a `InvalidModule` if it doesn't contain a Craftr module
    declaration. If the module exposes an identifier that is already
    used in the session, a `RuntimeError` is raised. '''

    filename = utils.path.normpath(filename)
    try:
      module = self._mod_filecache[filename]
    except KeyError:
      module = Module(self, filename)
      module.read_identifier()  #< InvalidModule
      if module.identifier in self._mod_idcache:
        other = self._mod_idcache[module.identifier]
        msg = "Module identifier clash {0!r} -- {1!r} ('{2}')"
        msg = msg.format(module.filename, other.filename, module.identifier)
        raise RuntimeError(msg)

    if module.identifier and module.identifier not in self._mod_idcache:
      self._mod_idcache[module.identifier] = module
      self._mod_filecache[filename] = module

    if register:
      self._register_module(module)
    return module

  def module_logger(self, module):
    ''' Factory to create a logger for a module. '''

    prefix = utils.proxy.LocalProxy(lambda: '  [{}]'.format(module.identifier))
    level = utils.proxy.LocalProxy(lambda: self.logger.level)
    logger = logging.Logger(prefix=prefix, level=level)
    return logger

  def info(self, *args, **kwargs):
    self.logger.info(*args, **kwargs)

  def warn(self, *args, **kwargs):
    self.logger.warn(*args, **kwargs)

  def error(self, *args, **kwargs):
    code = kwargs.pop('code', 1)
    self.logger.error(*args, **kwargs)
    if code:
      sys.exit(code)


class Module(object):
  ''' A module represents a unique entity in the build environment that
  exposes data and targets to the system for export (eg. to Ninja files).
  Every module has its unique identifier and namespace.

  A Craftr module is a special Python script that can declare build
  definitions. Modules are part of the Craftr ecosystem that is managed
  by a `Session` object. Every module has a unique identifier which it
  must declare in the file header like so

      # craftr_module(module_name)

  The module name must be a valid Python identifier and may contain
  dots to indicate namespaces. Any module may be submodule of another
  from its identifier. Other modules can be access from within a module
  using Python Syntax as you would expect. Here's a script that shows
  some of the available functionality.

  ```python
  # craftr_module(project)
  load('some.other.project')
  info("We're located in", project_dir)
  warn("But. B-baka! Did you check", some.other.project.Greeting, "?")
  error("Now, this is really serious. This will automatically exit.")
  ```
  '''

  def __init__(self, session, filename):
    super().__init__()
    self.filename = filename
    self.session = session  # todo: cyclic reference
    self.identifier = None
    self.logger = session.module_logger(self)
    self.locals = None
    self.executed = False
    self.targets = {}

  def __repr__(self):
    if self.identifier:
      return '<Module {0!r}>'.format(self.identifier)
    else:
      return '<Module at {0!r}>'.format(self.filename)

  def _init_locals(self, data=None):
    data = data or self.locals
    data.__name__ = '__craftr__'
    data.__file__ = self.filename
    data.G = self.session.get_namespace('globals')
    data.project_dir = os.path.dirname(self.filename)
    data.session = self.session
    data.module = self  # note: cyclic reference
    data.self = self.locals # note: cyclic reference
    data.load_module = self.load_module
    data.defined = self.defined
    data.setdefault = self.setdefault
    data.target = self.target
    data.info = self.info
    data.warn = self.warn
    data.error = self.error

  def read_identifier(self):
    ''' Reads the identifier from the file with the name the `Module`
    was initialized with and fills it into `Module.filename`. If the
    file does not expose an identifier, a `ValueError` is raised. The
    module locals will be initialized from this function. '''

    if self.identifier is not None:
      raise RuntimeError('identifier already read', self.identifier)
    assert self.locals is None

    identifier = None
    with open(self.filename) as fp:
      had_hash = False
      for line in fp:
        if not line.startswith('#') and had_hash:
          break
        elif line.startswith('#'):
          had_hash = True
          match = re.match('^#\s*craftr_module\(([^\s]+)\)\s*$', line)
          if match:
            identifier = match.group(1)
    if not identifier or not utils.validate_ident(identifier):
      raise InvalidModule(self.filename)

    self.identifier = identifier
    self.locals = utils.DataEntity('module:{0}'.format(self.identifier))
    self.logger.prefix = ' [{}]: '.format(self.identifier)
    self._init_locals()
    return identifier

  def execute(self, filename=None):
    ''' Execute the module's main script (the `Module.filename`) or
    a specific file (which is used for `Module.include`) in the modules
    scope. '''

    assert self.identifier is not None
    filename = filename or self.filename
    with open(filename) as fp:
      code = compile(fp.read(), filename, 'exec')
      try:
        exec(code, vars(self.locals), vars(self.locals))
      except ModuleReturnException:
        pass
    self.executed = True

  def extends(self, name):
    ''' Loads the module with the specified *name* and adds it as an
    entitiy dependency to the `Module.locals`. This will result in
    attribute lookups to be redirected to the dependency if it could
    not be found on the original object. '''

    entity = self.load_module(name)
    self.locals.__entity_deps__.append(entity)
    return entity

  def load_module(self, name):
    ''' Loads the module with the specicied *name* and returns it. The
    root namespace will automatically be inserted into the local
    namespace.

    Arguments:
      name (str or utils.DataEntity): The name of the module to load
        or an `utils.DataEntity` object that represents the namespace
        of the module to load.

        project = load_module('foo.project')
        assert foo.project is project
    '''

    if not isinstance(name, str):
      if not name.__entity_id__.startswith('ns:'):
        raise ValueError('need a namespace DataEntity')
      name = name.__entity_id__[3:]

    module = self.session.load_module(name)
    self.get_namespace(name.split('.')[0])
    return module.locals

  def get_namespace(self, name):
    ''' Loads the namespace with the specified *name* and returns it.
    The root namespace will automatically be inserted into the local
    namespace. Using this function, you can create a namespace before
    the module occupying that namespace is loaded.

        project = get_namespace('foo.project')
        assert foo.project is project
        project.Debug = True
        load_module(project)  # or
        load_module('foo.project')
        print(project)
    '''

    module = self.session.get_namespace(name)
    root_name = name.split('.')[0]
    root = self.session.get_namespace(root_name)
    setattr(self.locals, root_name, root)
    return module

  def defined(self, varname):
    ''' Returns True if the variable *varname* is defined. The variable
    name may contain periods to specify the member if a namespace. The
    variable will be resolved in the context of the unit, meaning that
    the variable is resolved from the local namespace. '''

    value = self.locals
    for part in varname.split('.'):
      try:
        value = getattr(value, part)
      except AttributeError:
        return False
    return True

  def setdefault(self, name, default, check_globals=True):
    ''' This function makes sure that the variable with the specified
    *name* is available in the scope of the module. If there is not
    already a value assigned to this name, *default* will be used. If
    *check_globals* is True, the global namespace is also checked for
    the existence of this value and that value is used instead of the
    *default*.

    Example:

        setdefault('Debug', False)
        if Debug:
          # do stuff
        else:
          # do other stuff
    '''

    try:
      value = getattr(self.locals, name)
    except AttributeError:
      pass
    if check_globals and 'value' not in locals():
      try:
        value = getattr(self.locals.G, name)
      except AttributeError:
        pass
    if 'value' not in locals():
      value = default

    setattr(self.locals, name, value)
    return value

  def target(self, name, **kwargs):
    ''' Declares a target with the specified *name*. The target will
    automatically be inserted into the modules scope by the *name*.

    Arguments:
      name (str): The name of the target.
      inputs (list): A list of input filenames.
      outputs (list): A list of output filenames.
      foreach (bool): True if the command should be executed for
        each item in the inputs and outputs separately, False if it
        should be executed once.
      command (list of str): A list of arguments to build the outputs.
      commandX (list of str): Optional additional command to execute.
        X can be any number between 0 and 9.
      target_class (Target subclass): Optional target class to use
        instead of the default class.
    '''

    if hasattr(self.locals, name):
      raise ValueError('target definition would override local variable', name)

    target_class = kwargs.pop('target_class', Target)
    target = target_class(self, name, **kwargs)
    self.targets[name] = target
    setattr(self.locals, name, target)
    return target

  def return_(self):
    ''' Raises a `ModuleReturnException` which can be done from the
    modules execution to end the script pre-emptively without causing
    an error. '''

    raise ModuleReturnException()

  def info(self, *args, **kwargs):
    self.logger.info(*args, **kwargs)

  def warn(self, *args, **kwargs):
    self.logger.warn(*args, **kwargs)

  def error(self, *args, **kwargs):
    code = kwargs.pop('code', 1)
    self.logger.error(*args, **kwargs)
    if code:
      raise ModuleError(self, code)


class Target(object):
  ''' This class represents a target that produces output files from a
  number of input files by using one or more commands. A command must be
  a list of arguments (with the first being the name of the program to
  invoke). The command may contain the placeholders `craftr.IN` and
  `craftr.OUT` that shall be replaced by the input and output files
  during export or invokation respectively.

  The arguments to this function are automatically expanded to lists
  using the `craftr.utils.lists.autoexpand()` function. '''

  def __init__(self, module, name, inputs, outputs, foreach=False, **commands):
    from craftr.utils.lists import autoexpand

    inputs = autoexpand(inputs)
    outputs = autoexpand(outputs)

    if not isinstance(module, Module):
      raise TypeError('<module> must be a Module object', type(module))
    if not isinstance(name, str):
      raise TypeError('<name> must be a string', type(name))
    if not utils.validate_var(name):
      raise ValueError('invalid target name', name)

    super().__init__()
    self.module = module
    self.name = name
    self.inputs = inputs
    self.outputs = outputs
    self.foreach = foreach
    self.commands = []

    for key, value in sorted(commands.items(), key=lambda x: x[0]):
      if not re.match('command\d?$', key):
        raise TypeError('unexpected keyword argument ' + key)
      if not isinstance(value, list):
        raise TypeError('<' + key + '> must be a list', type(value))
      self.commands.append(autoexpand(value))

  def __repr__(self):
    return "<Target '{0}'>".format(self.identifier)

  @property
  def identifier(self):
    return self.module.identifier + '.' + self.name


class NoSuchModule(Exception):
  ''' Raised when a module could not be found or if it was attempted to
  be retrieved from the cache and didn't exist. '''

  def __init__(self, name, required_by, mode):
    assert mode in ('get', 'load')
    super().__init__()
    self.name = name
    self.required_by = required_by
    self.mode = mode

  def __str__(self):
    if self.required_by:
      result = "'{0}' (required by '{1}') ".format(self.name, self.required_by)
    else:
      result = "'{0}' ".format(self.name)
    if self.mode == 'get':
      result += 'does not exist'
    else:
      result += 'could not be found'
    return result


class InvalidModule(Exception):
  ''' Raised when a Module file was invalid, that is if it does not
  expose a `craftr_module(<identifier>)` declaration. '''

  def __init__(self, filename):
    super().__init__()
    self.filename = filename

  def __str__(self):
    return "'{0}' exposes no craftr_module() declaration"


class ModuleError(Exception):
  ''' Raised from within `Module.error()` which can be called from a
  module script to indicate that a fatal error occured and the program
  shall not continue. '''

  def __init__(self, origin, code=1):
    self.origin = origin
    self.code = code

  def __str__(self):
    return "error '{0}' ({1})".format(self.origin.identifier, self.code)


class ModuleReturnException(Exception):
  pass



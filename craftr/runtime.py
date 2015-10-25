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

  class NamespaceProxy(utils.proxy.Proxy):
    __slots__ = utils.proxy.Proxy.__slots__ + ('_session', '_namespace')
    def __init__(self, session, namespace):
      super().__init__(self.__target)
      self._session = session
      self._namespace = namespace
    def __target(self):
      return self._session.namespaces[self._namespace]

  def __init__(self, action, cwd=None, logger=None):
    super().__init__()
    self.action = action
    self.path = []
    self.path.append(cwd or os.getcwd())
    self.path.append(os.path.join(os.path.dirname(__file__), 'builtins'))
    self.path.extend(os.getenv('CRAFTR_PATH', '').split(os.path.sep))
    self.globals = utils.DataEntity('session_globals')
    self.modules = {}
    self.namespaces = {}
    self.logger = logger or logging.Logger()
    self.main_module = None
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
    Returned will be an `utils.proxy.Proxy` that references the
    namespace entry. '''

    if not utils.ident.validate(name):
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

  def resolve_target(self, name, parent=None):
    ''' Resolves the *name* and returns the `Target` object for it.
    If *name* is a relative identifier, *parent* must be a string or
    `Module` object that represents the parent identifier to use. '''

    if isinstance(parent, Module):
      parent = parent.identifier
    if not utils.ident.validate(name):
      raise ValueError('invalid target identifier', name)
    modname, target = utils.ident.split(utils.ident.abs(name, parent))
    module = self.get_module(modname)
    if target not in module.targets:
      raise ValueError('no such target', target)
    return module.targets[target]

  def load_module(self, name, required_by=None, allow_reload=True, register=True):
    ''' Searches for a module in the `Session.path` list and all first-
    level subdirectories of the search path. Module filenames must be
    called `Craftfile` or be suffixed with `.craftr`. A Module must
    contain a Craftr module declaration:

        # craftr_module(module_name)

    If the *register* parameter is False, the module won't be executed
    and registered to the session as an active module. Of course, if a
    module that was already loaded is requested, it will still be
    loaded.
    '''

    if required_by is not None and not isinstance(required_by, Module):
      raise TypeError('expected Module for required_by', type(required_by))

    if not utils.ident.validate(name):
      raise ValueError('invalid module identifier', name)

    try:
      return self.modules[name]
    except KeyError:
      pass

    try:
      module = self._mod_idcache[name]
    except KeyError:
      pass
    else:
      if register:
        self._register_module(module)
      return module

    if not allow_reload:
      raise NoSuchModule(name, required_by, 'load')

    for path in utils.path.iter_tree(self.path, depth=2):
      if not os.path.isfile(path):
        continue
      if os.path.basename(path) == 'Craftfile' or path.endswith('.craftr'):
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

    from .utils.proxy import Proxy

    prefix = Proxy(lambda: '[{}] '.format(module.identifier))
    level = Proxy(lambda: self.logger.level)
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
    self.default_target = None
    self.targets = {}
    self.pools = {}

  def __repr__(self):
    if self.identifier:
      return '<Module {0!r}>'.format(self.identifier)
    else:
      return '<Module at {0!r}>'.format(self.filename)

  def _init_locals(self, data=None):
    data = data or self.locals

    # Pythonic globals
    data.__name__ = '__craftr__'
    data.__file__ = self.filename

    # General globals
    data.G = self.session.get_namespace('globals')
    data.session = self.session
    data.module = self  # note: cyclic reference
    data.self = self.locals  # note: cyclic reference
    data.project_dir = os.path.dirname(self.filename)

    # Module member functions exposed
    data.append_search_path = self.append_search_path
    data.extends = self.extends
    data.load_module = self.load_module
    data.get_namespace = self.get_namespace
    data.defined = self.defined
    data.setdefault = self.setdefault
    data.target = self.target
    data.pool = self.pool
    data.return_ = self.return_

    # Logging built-ins
    data.info = self.__info
    data.warn = self.__warn
    data.error = self.__error

    # Utility built-ins
    data.join = craftr.utils.path.join
    data.dirname = craftr.utils.path.dirname
    data.normpath = craftr.utils.path.normpath
    data.basename = craftr.utils.path.basename
    data.glob = craftr.utils.path.glob
    data.move = craftr.utils.path.move
    data.addprefix = craftr.utils.path.addprefix
    data.addsuffix = craftr.utils.path.addsuffix
    data.rmvsuffix = craftr.utils.path.rmvsuffix
    data.autoexpand = craftr.utils.lists.autoexpand
    data.Process = craftr.utils.shell.Process
    data.CommandBuilder = craftr.utils.CommandBuilder

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
        if not line.startswith('#') and (had_hash or line.strip() != ''):
          break
        elif line.startswith('#'):
          had_hash = True
          match = re.match('^#\s*craftr_module\(([^\s]+)\)\s*$', line)
          if match:
            identifier = match.group(1)
    if not identifier or not utils.ident.validate(identifier):
      raise InvalidModule(self.filename)

    self.identifier = identifier
    self.locals = utils.DataEntity('module:{0}'.format(self.identifier))
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

  def append_search_path(self, path):
    ''' Appends *path* to the `Session.path` list. A relative pathname
    will be considered relative to the project directory. '''

    path = utils.path.normpath(path, self.locals.project_dir)
    self.session.path.append(path)

  def extends(self, name):
    ''' Loads the module with the specified *name* and adds it as an
    entitiy dependency to the `Module.locals`. This will result in
    attribute lookups to be redirected to the dependency if it could
    not be found on the original object. '''

    if not isinstance(name, str):
      raise TypeError('expected str', type(name))

    module = self.session.load_module(name, required_by=self, register=False)
    self.execute(module.filename)

  def load_module(self, __module_name, **preconditions):
    ''' Loads the module with the specicied *name* and returns it. The
    root namespace will automatically be inserted into the local
    namespace. The *\*\*preconditions* are inserted into the namespace
    before the module is loaded. If the module is already loaded and any
    preconditions are specified and they don't match with the existing value,
    a `RuntimeError` is raised.

    Arguments:
      __module_name (str or utils.DataEntity): The name of the module to load
        or an `utils.DataEntity` object that represents the namespace
        of the module to load.

        project = load_module('foo.project', debug=True)
        assert foo.project is project
    '''

    __module_name = utils.proxy.resolve_proxy(__module_name)
    if isinstance(__module_name, utils.DataEntity):
      eid = __module_name.__entity_id__
      if not eid.startswith('ns:'):
        raise ValueError('need a namespace entity, got {!r}'.format(eid))
      __module_name = eid[3:]
    elif not isinstance(__module_name, str):
      raise TypeError('expected str or namespace DataEntity')

    module = self.session.modules.get(__module_name)
    if module:
      # Check if any preconditions conflict.
      for key, value in preconditions.items():
        if not hasattr(module.locals, key) or getattr(module.locals, key) != value:
          raise PreconditionConflictError(module, key, value)
    else:
      # Assign the preconditions to the namespace.
      ns = self.session.get_namespace(__module_name)
      for key, value in preconditions.items():
        setattr(ns, key, value)

    module = self.session.load_module(__module_name, required_by=self)
    self.get_namespace(__module_name.split('.')[0])
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

    try:
      obj, key = self._resolve(varname)
      getattr(obj, key)
    except AttributeError:
      return False
    return True

  def setdefault(self, name, default, check_globals=True, set_global=False):
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

    obj, key = self._resolve(name)
    try:
      value = getattr(obj, key)
    except AttributeError:
      pass
    if check_globals and obj is self.locals and 'value' not in locals():
      try:
        value = getattr(self.locals.G, key)
      except AttributeError:
        pass
    if 'value' not in locals():
      value = default

    setattr(obj, key, value)
    if set_global:
      setattr(self.locals.G, key, value)
    return value

  def get(self, name, default=NotImplemented, check_globals=True):
    ''' Resolves the variable *name* and returns its value or the
    *default* if specified. `AttributeError` will be raised if the
    *default* is not specified and the lookup failed. '''

    obj, key = self._resolve(name)
    try:
      return getattr(obj, key)
    except AttributeError:
      if default is NotImplemented:
        raise
      if check_globals and obj is self.locals:
        try:
          return getattr(self.locals.G, key)
        except AttributeError:
          if default is NotImplemented:
            raise
    return default

  def pool(self, name=None,_parent_frame=None, **kwargs):
    ''' Declare a job pool with the specified *name*. If *name* is
    omitted, the name is deduced from the variable that the result of
    this function is assigned to. The keyword arguments are passed to
    the `Pool` constructor. '''

    if not name:
      if not _parent_frame:
        _parent_frame = self._get_global_frame()
      try:
        name = utils.dis.get_assigned_name(_parent_frame)
      except ValueError as exc:
        raise RuntimeError('assigned name could not be derived', exc)
      if '.' in name:
        raise RuntimeError('target name can not be dotted', name)

    self.pools[name] = Pool(self, name, **kwargs)
    setattr(self.locals, name, self.pools[name])
    return self.pools[name]

  def target(self, name=None, _parent_frame=None, default=False, **kwargs):
    ''' Declares a target with the specified *name*. The target will
    automatically be inserted into the modules scope by the *name*.

    Arguments:
      name (str): The name of the target. If None, it will automatically
        be derived from the variable name that the result of this function
        is assigned to. This is the preferred way to declare targets.
      _parent_frame (frame): If *name* is not specified and this function
        is called from a rule function (ie. not directly in the actual
        module), this parameter should be passed the frame that called
        rule function to be able to derive the assigned variable name.
      default (bool): True if this target should be declared the
        default target that is to be built. Only the default target of
        the current main Craftr module is used, not the default targets
        of all loaded modules.
      inputs (list): A list of input filenames.
      outputs (list): A list of output filenames.
      foreach (bool): True if the command should be executed for
        each item in the inputs and outputs separately, False if it
        should be executed once.
      command (list of str): A list of arguments to build the outputs.
      commandX (list of str): Optional additional command to execute.
        X can be any number between 0 and 9.
    '''

    if not name:
      if not _parent_frame:
        _parent_frame = self._get_global_frame()
      try:
        name = utils.dis.get_assigned_name(_parent_frame)
      except ValueError as exc:
        raise RuntimeError('assigned name could not be derived', exc)
      if '.' in name:
        raise RuntimeError('target name can not be dotted', name)

    if hasattr(self.locals, name):
      raise ValueError('target definition would override local variable', name)

    target = Target(self, name, **kwargs)
    self.targets[name] = target
    setattr(self.locals, name, target)
    if default:
      self.default_target = target
    return target

  def return_(self):
    ''' Raises a `ModuleReturnException` which can be done from the
    modules execution to end the script pre-emptively without causing
    an error. '''

    raise ModuleReturnException()

  def _resolve(self, varname):
    ''' Resolves a variable name and returns a tuple of `(obj, key)`
    where *obj* is the object that is supposed to be accessed for
    the attribute *key*. Raises an `AttributeError` if a variable
    can not be resolved in the way to *obj*. '''

    obj = self.locals
    parts = varname.split('.')
    for part in parts[:-1]:
      obj = getattr(obj, part)
    return (obj, parts[-1])

  def _get_global_frame(self):
    ''' Returns the closest stack frame that is executed in this modules
    local scope as global variables. To say it in different words, this is
    the frame of the global scope of the module's script. '''

    # Find the frame that is executed for this module.
    frame = sys._getframe(1)
    while frame:
      if frame.f_locals is vars(self.locals):
        break
      frame = frame.f_back
    if not frame:
      raise RuntimeError('module frame could not be found')
    return frame

  def __info(self, *args, **kwargs):
    self.logger.info(*args, frame=sys._getframe().f_back, **kwargs)

  def __warn(self, *args, **kwargs):
    self.logger.warn(*args, frame=sys._getframe().f_back, **kwargs)

  def __error(self, *args, **kwargs):
    code = kwargs.pop('code', 1)
    self.logger.error(*args, frame=sys._getframe().f_back, **kwargs)
    if code:
      message = craftr.logging.print_as_str(*args)
      raise ModuleError(self, code, message)


class _ModuleObject(object):
  ''' Represents an object that is part of a Craftr module. '''

  def __init__(self, module, name):
    super(_ModuleObject, self).__init__()
    self.module = module
    self.name = name

  def __repr__(self):
    return '<{} {!r}>'.format(type(self).__name__, self.name)

  @property
  def identifier(self):
    return '{}.{}'.format(self.module.identifier, self.name)


class Target(_ModuleObject):
  ''' This class represents a target that produces output files from a
  number of input files by using one or more commands. A command must be
  a list of arguments (with the first being the name of the program to
  invoke). The command may contain the placeholders `craftr.IN` and
  `craftr.OUT` that shall be replaced by the input and output files
  during export or invokation respectively.

  The arguments to this function are automatically expanded to lists
  using the `craftr.utils.lists.autoexpand()` function.

  Arguments:
    module (Module): The module object that the target is created in.
    name (str): The name of the target which must be a valid identifier.
    inputs (list of str): A list of input files (may be nested).
    outputs (list of str): A list of output files (may be nested).
    requires (list of str): A list of additional requirements
      (filenames) that need to be available before the target is
      built.
    foreach (bool): If True, the *command* is executed for each pair
      of input and output files. The length of *inputs* and *outputs*
      must be the same.
    description (str): Description of the target.
    pool (str or Pool): If a string is passed, it must be the absolute
      name of a pool. A special case is the "console" pool (see the ninja
      documentation for more information). Otherwise, it must be a `Pool`
      object.
    command (str): The command to execute for the target.
    commandX (str): Additional commands to execute for the target,
      where X stands for a digit between 0 and 9. The commands are
      executed in order, with *command* as the first.
    meta_* (any): Specify meta data of the target which can be
      read from the `Target.meta` dictionary. The `meta_` part
      is stripped from the key.


  Meta Values:
    type (str): The type the target produces, eg. `'objects'`, `'executable'`,
      `'shared_library'` or `'static_library'`.
    includes (list of str): Eg. for a `'static_library'` or `'shared_library'`,
      this can be a list of include directories that are required to use the
      library. That should automatically be handled by rule functions.
    defines (list of str): Same as for *includes*, a list of preprocessor
      definitions that are used for a static or shared library.
    deps (str): If set, can be `gcc` or `msvc`. Handled by the Ninja backend.
    depfile (str): A dependency file, handled by the Ninja backend. Usually,
      you want to set it to `'%%out.d'`.
  '''

  def __init__(self, module, name, inputs, outputs, requires=(),
      foreach=False, description=None, pool=None, **kwargs):
    super().__init__(module, name)
    from craftr.utils.lists import autoexpand

    inputs = autoexpand(inputs)
    outputs = autoexpand(outputs)
    requires = autoexpand(requires)

    if not isinstance(module, Module):
      raise TypeError('<module> must be a Module object', type(module))
    if not isinstance(name, str):
      raise TypeError('<name> must be a string', type(name))
    if not utils.ident.validate_var(name):
      raise ValueError('invalid target name', name)
    if pool is not None and pool != 'console' and not isinstance(pool, Pool):
      raise TypeError('pool must be Pool instance or "console"')

    self.inputs = inputs
    self.outputs = outputs
    self.requires = requires
    self.foreach = foreach
    self.description = description
    self.pool = pool
    self.commands = []
    self.meta = {}

    for key, value in tuple(kwargs.items()):
      if key.startswith('meta_'):
        name = key[5:]
        if name:
          self.meta[name] = value
          kwargs.pop(key)

    for key, value in sorted(kwargs.items(), key=lambda x: x[0]):
      if not re.match('command\d?$', key):
        raise TypeError('unexpected keyword argument ' + key)
      if not isinstance(value, list):
        raise TypeError('<' + key + '> must be a list', type(value))
      self.commands.append(autoexpand(value))

  def __iter__(self):
    return iter(self.outputs)


class Pool(_ModuleObject):
  ''' Represents a pool in which jobs are executed. '''

  def __init__(self, module, name, depth=None):
    super(Pool, self).__init__(module, name)
    if depth is not None and not isinstance(depth, int):
      raise TypeError('depth must be None or int')
    self.depth = depth


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
    return "'{}' exposes no craftr_module() declaration".format(self.filename)


class ModuleError(Exception):
  ''' Raised from within `Module.error()` which can be called from a
  module script to indicate that a fatal error occured and the program
  shall not continue. '''

  def __init__(self, origin, code=1, message=None):
    self.origin = origin
    self.code = code
    self.message = message

  def __str__(self):
    res = 'error in "{}": '.format(self.origin.identifier)
    if self.message:
      res += self.message.strip()
    return res + ' (code:{})'.format(self.code)


class ModuleReturnException(Exception):
  pass


class PreconditionConflictError(Exception):
  ''' This exception is raised if `Module.load_module()` defines any
  precondition, the module was already loaded and the precondition
  doesn't match the existing value. '''

  def __init__(self, module, key, value):
    self.module = module
    self.key = key
    self.value = value

  def __str__(self):
    message = 'Conflicting precondition "{0}.{1}" '
    if not hasattr(self.module.locals, self.key):
      message += 'has no value'
      has_value = None
    else:
      message += 'has value {2!r}'
      has_value = getattr(self.module.locals, self.key)
    message += ', required {3!r}'
    return message.format(self.module.identifier, self.key, has_value, self.value)

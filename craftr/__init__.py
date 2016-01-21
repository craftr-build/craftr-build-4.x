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

import os
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
  ''' This class manages a build session and encapsulates all Craftr
  modules and :class:`Targets<Target>`.

  .. attribute:: cwd

    The original working directory from which Craftr was invoked, or
    the directory specified with the ``-p`` command-line option. This
    is different than the current working directory since Craftr changes
    to the build directory immediately.

  .. attribute:: env

    A dictionary of environment variables, initialized as a copy of
    :data:`os.environ`. In a Craftfile, you can use :data:`os.environ`
    or the alias :data:`craftr.environ` instead, which is more convenient
    that accessing ``session.env``.

  .. attribute:: path

    A list of search paths for Craftr extension modules. See :doc:`ext`.

  .. attribute:: modules

    A dictionary of Craftr extension modules. Key is the module name
    without the ``craftr.ext.`` prefix.

  .. attribute:: targets

    A dictionary mapping the full identifier to :class:`Target` objects
    that have been declared during the build session. When the Session
    is created, a ``clean`` Target which calls ``ninja -t clean`` is
    always created automatically.

  .. attribute:: server

    An :class:`rts.CraftrRuntimeServer` object that is started when
    the session context is entered with :func:`magic.enter_context`
    and stopped when the context is exited. See :meth:`on_context_enter`.

  .. attribute:: server_bind

    A tuple of ``(host, port)`` which the :attr:`server` will be
    bound to when it is started. Defaults to None, in which case
    the server is bound to the localhost on a random port.

  .. attribute:: rts_funcs

    A dictionary that maps target names to functions. The function will
    be invoked when you call ``craftr-rts <func_name>`` (note: the
    Craftr Runtime Server must be running and the environment variable
    ``CRAFTR_RTS`` must be set). The functions added to this dictionary
    must accept a list of command-line arguments.

  .. attribute:: ext_importer

    A :class:`ext.CraftrImporter` object that handles the importing of
    Craftr extension modules. See :doc:`ext`.

  .. attribute:: var

    A dictionary of variables that will be exported to the Ninja manifest.

  .. attribute:: verbosity

    The logging verbosity level. Defaults to 0. Used by the logging
    functions :func:`debug`, :func:`info`, :func:`warn` and :func:`error`.

  .. attribute:: strace_depth:

    The logging functions may print a stack trace of the log call when
    the verbosity is high enough. This defines the depth of the stack
    trace. Defaults to 3.

  .. attribute:: export

    This is set to True when the ``-e`` option was specified on the
    command-line, meaning that a Ninja manifest will be exported. Some
    projects eventually need to export additional files before running
    Ninja, for example with :meth:`TargetBuilder.write_command_file`.
  '''

  def __init__(self, cwd=None, path=None, server_bind=None, verbosity=0,
      strace_depth=3, export=False):
    super().__init__()
    self.cwd = cwd or os.getcwd()
    self.env = environ.copy()
    self.server = rts.CraftrRuntimeServer(self)
    self.server_bind = server_bind
    self.rts_funcs = {}
    self.ext_importer = ext.CraftrImporter(self)
    self.path = [craftr.path.join(craftr.path.dirname(__file__), 'lib')]
    self.modules = {}
    self.targets = {}
    self.var = {}
    self.verbosity = verbosity
    self.strace_depth = strace_depth
    self.export = export

    if path is not None:
      self.path.extend(path)

    self.targets['clean'] = Target(
      command = 'ninja -t clean',
      inputs = None,
      outputs = None,
      name = 'clean',
      module = None,
      explicit = True)

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
    ''' Alias for :meth:`Session.ext_importer.update()<
    ext.CraftrImporter.update>`. '''

    self.ext_importer.update()

  def start_server(self):
    ''' Start the Craftr RTS server (see :attr:`Session.server`). It
    will automatically be stopped when the session context is exited. '''

    # Start the Craftr Server to enable cross-process invocation
    # of Python functions.
    if self.server_bind:
      self.server.bind(*self.server_bind)
    else:
      self.server.bind()
    self.server.serve_forever_async()
    environ['CRAFTR_RTS'] = '{0}:{1}'.format(self.server.host, self.server.port)
    debug('Started Craftr RTS at {0}:{1}'.format(self.server.host, self.server.port))

  def _stop_server(self):
    if self.server.running:
      self.server.stop()
      self.server.close()

  def on_context_enter(self, prev):
    ''' Called when entering the Session context with
    :func:`magic.enter_context`. Does the following things:

    * Sets up the :data`os.environ` with the values from :attr:`Session.env`
    * Adds the :attr:`Session.ext_importer` to :data:`sys.meta_path`
    * Starts the Craftr Runtime Server (:attr:`Session.server`) and sets
      the ``CRAFTR_RTS`` environment variable

    .. note:: A copy of the original :data:`os.environ` is saved and later
      restored in :meth:`on_context_leave`. The :data:`os.environ` object
      can not be replaced by another object, that is why we change its
      values in-place.
    '''

    if prev is not None:
      raise RuntimeError('session context can not be nested')

    # We can not change os.environ effectively, we must update the
    # dictionary instead.
    self._old_environ = environ.copy()
    environ.clear()
    environ.update(self.env)
    self.env = environ

    sys.meta_path.append(self.ext_importer)
    self.update()

  def on_context_leave(self):
    ''' Called when the context manager entered with
    :func:`magic.enter_context` is exited. Undos all of the stuff
    that :meth:`on_context_enter` did and more.

    * Stop the Craftr Runtime Server
    * Restore the :data:`os.environ` dictionary
    * Removes all ``craftr.ext.`` modules from :data:`sys.modules` and
      ensures they are in :attr:`Session.modules` (they are expected to
      be put there from the :class:`ext.CraftrImporter`).
    '''

    self._stop_server()

    # Restore the original values of os.environ.
    self.env = environ.copy()
    environ.clear()
    environ.update(self._old_environ)
    del self._old_environ

    sys.meta_path.remove(self.ext_importer)
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
  corresponding in- and output files. Will be rendered into a ``rule``
  and one or many ``build`` statements in the Ninja manifest.

  .. attribute:: name

    The name of the target. This is usually deduced from the
    variable the target is assigned to if no explicit name was
    passed to the :class:`Target` constructor. Note that the
    actual name of the generated Ninja rule must be read from
    :attr:`fullname`.

  .. attribute:: module

    The Craftr extension module this target belongs to. Defaults to
    the currently executed module (retrieved from the thread-local
    :data:`module`). Can be None, but only if there is no module
    currently being executed.

  .. attribute:: command

    A list of strings that represents the command to execute. A string
    can be passed to the constructor in which case it is parsed with
    :func:`shell.split`.

  .. attribute:: inputs

    A list of filenames that are listed as inputs to the target and
    that are substituted for ``$in`` and ``$in_newline`` during the
    Ninja execution. Can be None. The :class:`Target` constructor
    expands the passed argument with :func:`expand_inputs`, thus
    also accepts a single filename, Target or a list with Targets
    and/or filenames.

  .. attribute:: outputs

    A list of filenames that are listed as outputs of the target and
    that are substituted for ``$out`` during the Ninja execution.
    Can be None. The :class:`Target` constructor accepts a list of
    filenames or a single filename for this attribute.

  .. attribute:: implicit_deps

      A list of filenames that are required to build the Target,
      additionally to the :attr:`inputs`, but are not expanded by
      the ``$in`` variable in Ninja. See "Implicit dependencies"
      in the `Ninja Manual`_.

  .. attribute:: order_only_deps

    See "Order-only dependencies" in the `Ninja Manual`_.

  .. attribute:: foreach

    If this is set to True, the number of :attr:`inputs` must match
    the number of :attr:`outputs`. Instead of generating a single
    ``build`` instruction in the Ninja manifest, an instruction for
    each input/output pair will be created instead. Defaults to False.

  .. attribute:: description

    A description of the Target. Will be added to the generated Ninja
    rule. Defaults to None.

  .. attribute:: pool

    The name of the build pool. Defaults to None. Can be ``"console"``
    for Targets that don't actually build files but run a program. Craftr
    will treat Targets in that pool as if :attr:`explicit` is True.

  .. attribute:: deps

    The mode for automatic dependency detection for C/C++ targets.
    See the "C/C++ Header Depenencies" section in the `Ninja Manual`_.

  .. attribute:: depfile

    A filename that contains additional dependencies.

  .. attribute:: msvc_deps_prefix

    The MSVC dependencies prefix to be used for the rule.

  .. attribute:: frameworks

    A list of :class:`Frameworks<Framework>` that are used by the Target.
    Rule functions that take other Targets as inputs can include this list.
    For example, a C++ compiler might add a Framework with ``libs = ['c++']``
    to a Target so that the Linker to which the C++ object files target is
    passed automatically knows to link with the ``c++`` library.

    Usually, a rule function uses the :class:`TargetBuilder` (which
    internally uses :meth:`expand_inputs`) to collect all Frameworks
    used in the input targets.

  .. attribute:: explicit

    If True, the target will only be built by Ninja if it is explicitly
    specified on the command-line or if it is required by another target.
    Defaults to False.

  .. automethod:: Target.__lshift__

  .. _Ninja Manual: https://ninja-build.org/manual.html
  '''

  def __init__(self, command, inputs=None, outputs=None, implicit_deps=None,
      order_only_deps=None, foreach=False, description=None, pool=None,
      var=None, deps=None, depfile=None, msvc_deps_prefix=None,
      explicit=False, frameworks=None, module=None, name=None):

    if not module and craftr.module:
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

    if module:
      targets = module.__session__.targets
      if self.fullname in targets:
        raise ValueError('target {0!r} already exists'.format(self.fullname))
      targets[self.fullname] = self

  def __repr__(self):
    pool = ' in "{0}"'.format(self.pool) if self.pool else ''
    command = ' running "{0}"'.format(self.command[0])
    return '<Target {self.fullname!r}{command}{pool}>'.format(**locals())

  def __lshift__(self, other):
    ''' Shift operator to add to the list of :attr:`implicit_deps`.

    .. note:: If *other* is or contains a :class:`Target`, the targets
      frameworks are *not* added to this Target's framework list!
    '''

    # xxx: Should we append the frameworks of the input targets to the
    # frameworks of this target?
    self.implicit_deps += expand_inputs(other)
    return self

  __ilshift__ = __lshift__

  @staticmethod
  def _get_name(module):
    # Always use the frame of the current module, though.
    if craftr.module() != module:
      raise RuntimeError('target name deduction only available when '
        'used from the currently executed module')
    return magic.get_assigned_name(magic.get_module_frame(module, allow_local=False))

  @property
  def fullname(self):
    ''' The full identifier of the Target. If the Target is assigned
    to a :attr:`module`, this is the module name and the :attr:`Target.name`,
    otherwise the same as :attr:`Target.name`. '''

    if self.module:
      return self.module.project_name + '.' + self.name
    else:
      return self.name


class TargetBuilder(object):
  ''' This is a helper class to make it easy to implement rule functions
  that create a :class:`Target`. Rule functions usually depend on inputs
  (being files or other Targets that can also contain additional frameworks),
  rule-level settings and :class:`Frameworks<Framework>`. The TargetBuilder
  takes all of this into account and prepares the data conveniently.

  :param inputs: Inputs for the target. Processed by :func:`expand_inputs`.
    Use :attr:`TargetBuilder.inputs` instead of the argument you passed
    here to access the inputs. Must be a string, :class:`Target`, list or None.
  :param frameworks: A list of frameworks to take into account.
  :param kwargs: Additional keyword-arguments that have been passed to the
    rule-function. These will be turned into a new :class:`Framework` object.
    :meth:`create_target` will check if all arguments of this dictionary
    have been taken into account and will yield a warning if not.
  :param module:
  :param name:
  :param stacklevel:

  .. attribute:: caller

  .. attribute:: inputs

  .. attribute:: frameworks

  .. attribute:: kwargs

  .. attribute:: options

    A :class:`FrameworkJoin` object that is used to read settings from
    the list of frameworks collected from the input Targets, the
    additional frameworks specified to the :class:`TargetBuilder`
    constructor and the specified ``kwargs`` dictionary.

  .. attribute:: module

  .. attribute:: name

    The name of the Target that is being built.

  .. attribute:: target_attrs

    A dictonary of arguments that are set to the target after
    construction in :meth:`create_target`. Can only set attributes that
    are already attributes of the :class:`Target`.

  .. automethod:: TargetBuilder.__getitem__
  '''

  def __init__(self, inputs, frameworks, kwargs, module=None, name=None, stacklevel=1):
    self.caller = magic.get_caller(stacklevel + 1)
    frameworks = list(frameworks)
    self.inputs = expand_inputs(inputs, frameworks)
    self.frameworks = frameworks
    self.kwargs = kwargs
    self.options = FrameworkJoin(Framework(self.caller, kwargs), *frameworks)
    self.module = module or craftr.module()
    self.name = name
    self.target_attrs = {}
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
    ''' The full name of the Target that is being built. '''

    return self.module.project_name + '.' + self.name

  @property
  def target(self):
    ''' A dictonary of arguments that are set to the target after
    construction in :meth:`create_target`. Can only set attributes that
    are already attributes of the :class:`Target`.

    .. deprecated::
      Use :attr:`target_attrs` instead.
    '''

    return self.target_attrs

  def __getitem__(self, key):
    ''' Alias for :meth:`FrameworkJoin.__getitem__`. '''

    return self.options[key]

  def get(self, key, default=None):
    ''' Alias for :meth:`FrameworkJoin.get`. '''

    return self.options.get(key, default)

  def merge(self, key):
    ''' Alias for :meth:`FrameworkJoin.merge`. '''

    return self.options.merge(key)

  def log(self, level, *args, stacklevel=1, **kwargs):
    ''' Log function that includes the :attr:`fullname`. '''

    module_name = '{0}'.format(self.module.project_name, self.name)
    log(level, *args, module_name=module_name, stacklevel=stacklevel + 1, **kwargs)

  def invalid_option(self, option_name, option_value=_sentinel, cause=None):
    ''' Use this method in a rule function if you found the value of an
    option has an invalid option. You should raise a :class:`ValueError`
    on a fatal error instead. '''

    if option_value is _sentinel:
      option_value = self[option_name]
    message = 'invalid option: {0} = {1!r}'.format(option_name, option_value)
    if cause:
      message = '{0} ({1})'.format(message, cause)
    self.log('warn', message, stacklevel=2)

  def add_framework(self, __fw_or_name, __fw_dict=None, **kwargs):
    ''' Add or create a new Framework and add it to :attr:`options`
    and :attr:`frameworks`. '''

    if not isinstance(__fw_or_name, Framework):
      fw = Framework(__fw_or_name, __fw_dict, **kwargs)
    else:
      fw = __fw_or_name
    if fw not in self.frameworks:
      self.frameworks.append(fw)
    self.options += [fw]
    return fw

  def expand_inputs(self, inputs):
    ''' Wrapper for :func:`expand_inputs` that will add the Frameworks
    extracted from the *inputs* to :attr:`options` and :attr:`frameworks`. '''

    frameworks = []
    result = expand_inputs(inputs, frameworks)
    self.frameworks += frameworks
    self.options += frameworks
    return result

  def create_target(self, command, inputs=None, outputs=None, **kwargs):
    ''' Create a :class:`Target` and return it.

    :param command: The command-line for the Target.
    :param inputs: The inputs for the Target. If None, the
      :attr:`TargetBuilder.inputs` will be used instead.
    :param outputs: THe outputs for the Target.
    :param kwargs: Additional keyword arguments for the Target constructor.
      Make sure that none conflicts with the :attr:`target` dictionary.

    .. note:: This function will yield a warning when there are any keys
      in the :attr:`kwargs` dictionary that have not been read from the
      :class:`options`.
    '''

    # Complain about unhandled options.
    unused_options = self.kwargs.keys() - self.options.used_keys
    if unused_options:
      self.log('info', 'unused options for {0}():'.format(self.caller), unused_options, stacklevel=2)

    if inputs is None:
      inputs = self.inputs
    kwargs.setdefault('frameworks', self.frameworks)
    target = Target(command=command, inputs=inputs, outputs=outputs,
      module=self.module, name=self.name, **kwargs)
    for key, value in self.target_attrs.items():
      # We can only set attributes that the target already has.
      getattr(target, key)
      setattr(target, key, value)
    return target

  def write_command_file(self, arguments, suffix=None, always=False):
    ''' Writes a file to the `.cmd` folder in the builder directory (ie.
    the current directory) that contains the command-line arguments
    specified in *arguments*. The name of that file is the name of the
    Target that is created with this builder. Optionally, a suffix
    for that file can be specified to be able to write multiple such
    files. Returns the filename of the generated file. If *always* is
    set to True, the file will always be created even if `Session.export`
    is set to False. '''

    filename = '.cmd/{0}'.format(self.fullname)
    if always or session.export:
      path.makedirs('.cmd')
      if suffix:
        filename += suffix
      with open(filename, 'w') as fp:
        for arg in arguments:
          fp.write(shell.quote(arg))
          fp.write(' ')
    return filename


class Framework(dict):
  ''' A Framework represents a set of options that are to be taken
  into account by compiler classes. Eg. you might create a framework
  that contains the additional information and options required to
  compile code using OpenCL and pass that to the compiler interface.

  Compiler interfaces may also add items to :attr:`Target.frameworks`
  that can be taken into account by other target rules. :func:`expand_inputs()`
  returns a list of frameworks that are being used in the inputs.

  Use the :class:`FrameworkJoin` class to create an object to process the
  data from multiple frameworks.

  :param __fw_name: The name of the Framework. If omitted, the assigned
    name of the calling module will be used.
  :param __init_dict: A dictionary to initialize the Framework with.
  :param kwargs: Additional key/value pairs for the Framework. '''

  def __init__(self, __fw_name=None, __init_dict=None, **kwargs):
    super().__init__()
    if not __fw_name:
      __fw_name = Target._get_name(module())
    if __init_dict is not None:
      self.update(__init_dict)
    self.update(kwargs)
    self.name = __fw_name

  def __repr__(self):
    return 'Framework(name={0!r}, {1})'.format(self.name, super().__repr__())


class FrameworkJoin(object):
  ''' This class is used to process a set of :class:`Frameworks<Framework>`
  and retreive relevant information from it. For some options, you might
  want to read the first value that is specified in any of the frameworks,
  for another you may want to create a list of all values in the frameworks.
  This is what the FrameworkJoin allows you to do.

  .. code-block:: python

    >>> fw1 = Framework('fw2', defines=['DEBUG'])
    >>> fw2 = Framework(defines=['DO_STUFF'])
    >>> print(fw2.name)
    'fw2'
    >>> FrameworkJoin(fw1, fw2).merge('defines')
    ['DEBUG', 'DO_STUFF']

  .. attribute:: used_keys

    A set of keys that have been accessed via :meth:`__getitem__`,
    :meth:`get` and :meth:`merge`.

  .. attribute:: frameworks

    The list of :class:`Framework` objects.

  .. automethod:: FrameworkJoin.__iadd__
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

  def keys(self):
    ''' Returns a set of all keys in all frameworks. '''

    keys = set()
    for fw in self.frameworks:
      keys |= fw.keys()
    return keys


class ModuleError(RuntimeError):

  def __init__(self, module=None):
    self.module = module or craftr.module()


class ModuleReturn(Exception):
  pass


def return_():
  ''' Raise a :class:`ModuleReturn` exception, causing the module execution
  to be aborted and returning back to the parent module. Note that this
  function can only be called from a Craftr modules global stack frame,
  otherwise a :class:`RuntimeError` will be raised. '''

  if magic.get_frame(1).f_globals is not vars(module):
    raise RuntimeError('return_() can not be called outside the current '
      'modules global stack frame')
  raise ModuleReturn()


def expand_inputs(inputs, frameworks=None):
  ''' Expands a list of inputs into a list of filenames. An input is a
  string (filename) or a :class:`Target` object from which the
  :attr:`Target.outputs` are used. Returns a list of strings.

  If *frameworks* is specified, it must be a :class:`list` to which the
  frameworks of all input :class:`Target` objects will be appended. '''

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
  return session.ext_importer.import_file(filename)


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


def craftr_min_version(version_string):
  ''' Ensure the current version of Craftr is at least the version
  specified with *version_string*, otherwise call :func:`error()`. '''

  if __version__ < version_string:
    error('requires at least Craftr v{0}'.format(version_string))


from craftr.logging import log, debug, info, warn, error
from craftr import ext, path, shell, ninja, rts

__all__ = ['session', 'module', 'path', 'shell', 'environ',
  'Target', 'TargetBuilder', 'Framework', 'FrameworkJoin',
  'debug', 'info', 'warn', 'error', 'return_', 'expand_inputs',
  'import_file', 'import_module', 'craftr_min_version']

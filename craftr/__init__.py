# Copyright (C) 2016  Niklas Rosenstein
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
__version__ = '1.1.0'

import os
import sys
if sys.version < '3.4':
  raise EnvironmentError('Craftr minimum Python version is 3.4')

from os import environ
from craftr import magic

RTS_COMMAND = 'craftr-rts-invoke'  # Name of the Craftr RTS command
MANIFEST = 'build.ninja'           # Name of the exported Ninja manifest
CMDDIR = '.craftr-cmd'             # Temp directory for command files

session = magic.new_context('session')
module = magic.new_context('module')

import craftr
import collections
import functools
import itertools
import os
import stat
import traceback
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
    than accessing ``session.env``.

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

  .. attribute:: files_to_targets

    *New in v1.1.0* Maps the files produced by all targets to
    their producing :class:`Target` object. This dictionary is
    used for speeding up :meth:`find_target_for_file` and to
    check if any file would be produced by multiple targets.

    All keys in this dictionary are absolute filenames normalized
    with :func:`path.normpath`.

  .. attribute:: server

    An :class:`rts.CraftrRuntimeServer` object that is started when
    the session context is entered with :func:`magic.enter_context`
    and stopped when the context is exited. See :meth:`on_context_enter`.

  .. attribute:: server_bind

    A tuple of ``(host, port)`` which the :attr:`server` will be
    bound to when it is started. Defaults to None, in which case
    the server is bound to the localhost on a random port.

  .. attribute:: ext_importer

    A :class:`ext.CraftrImporter` object that handles the importing of
    Craftr extension modules. See :doc:`ext`.

  .. attribute:: var

    A dictionary of variables that will be exported to the Ninja manifest.

  .. attribute:: verbosity

    The logging verbosity level. Defaults to 0. Used by the logging
    functions :func:`debug`, :func:`info`, :func:`warn` and :func:`error`.

  .. attribute:: strace_depth

    The logging functions may print a stack trace of the log call when
    the verbosity is high enough. This defines the depth of the stack
    trace. Defaults to 3.

  .. attribute:: export

    This is set to True when the ``-e`` option was specified on the
    command-line, meaning that a Ninja manifest will be exported. Some
    projects eventually need to export additional files before running
    Ninja, for example with :meth:`TargetBuilder.write_command_file`.

  .. attribute:: buildtype

    The buildtype that was specified with the ``--buildtype``
    command-line option. This attribute has two possible values:
    ``'standard'`` and ``'external'``. Craftfiles and rule functions
    must take the buildtype into consideration. In ``'external'``
    mode, rule functions should consider external options wherever
    applicable, for example the ``CFLAGS`` environment variables
    instead or additionally to the standard flags for C source file
    compilation.

  .. attribute:: finalized

    True if the Session was finalized with :meth:`finalize`.
  '''

  def __init__(self, cwd=None, path=None, server_bind=None, verbosity=0,
      strace_depth=3, export=False, buildtype='standard'):
    if buildtype not in ('standard', 'external'):
      raise ValueError('invalid buildtype: {!r}'.format(buildtype))
    self.cwd = cwd or os.getcwd()
    self.env = environ.copy()
    self.server = rts.CraftrRuntimeServer(self)
    self.server_bind = server_bind
    self.ext_importer = ext.CraftrImporter(self)
    self.path = [craftr.path.join(craftr.path.dirname(__file__), 'lib')]
    self.modules = {}
    self.targets = {}
    self.files_to_targets = {}
    self.var = {}
    self.verbosity = verbosity
    self.strace_depth = strace_depth
    self.export = export
    self.buildtype = buildtype
    self.finalized = False

    if path is not None:
      self.path.extend(path)

    self.register_target(Target(
      command = 'ninja -t clean',
      inputs = None,
      outputs = None,
      name = 'clean',
      module = None,
      explicit = True))

  def register_target(self, target):
    ''' This function is used by the :class:`Target` constructor
    to register itself to the :class:`Session`. This will add the
    target to the :attr:`target` dictionary and also update the
    :attr:`files_to_targets` mapping.

    :param target: A :class:`Target` object
    :raise ValueError: If the name of the target is already reserved.
    :raise RuntimeError: If this target produces a file that is
      already produced by another arget.
    '''

    if self.finalized:
      raise RuntimeError('can not registered Target to finalized Session')

    files = []
    if target.outputs:
      # Check if any of the output files are already produced
      # by another target.
      for fn in target.outputs:
        if fn in self.files_to_targets:
          msg = '{!r} is already produced by another target: {!r}'
          raise RuntimeError(msg.format(fn, self.files_to_targets[fn].fullname))
        files.append(path.normpath(fn))

    if target.fullname in self.targets:
      raise ValueError('target name already reserved: {!r}'.format(target.fullname))
    self.targets[target.fullname] = target
    for fn in files:
      self.files_to_targets[fn] = target

  def find_target_for_file(self, filename):
    ''' Finds a target that outputs the specified *filename*. '''

    try:
      return self.files_to_targets[path.normpath(filename)]
    except KeyError:
      return None

  def finalize(self):
    ''' Finalize the session, setting up target dependencies based
    on their input/output files to simplify verifying dependencies
    inside of Craftr. The session will no longer accept target
    registrations. '''

    if self.finalized:
      raise RuntimeError('already finalized')
    for target in self.targets.values():
      target.finalize(self)
    self.finalized = True

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
    debug('rts listening at {0}:{1}'.format(self.server.host, self.server.port))

  def _stop_server(self):
    if self.server.running:
      self.server.stop()
      self.server.close()

  def on_context_enter(self, prev):
    ''' Called when entering the Session context with
    :func:`magic.enter_context`. Does the following things:

    * Sets up the :data:`os.environ` with the values from :attr:`Session.env`
    * Adds the :attr:`Session.ext_importer` to :data:`sys.meta_path`

    .. note:: A copy of the original :data:`os.environ` is saved and later
      restored in :meth:`on_context_leave`. The :data:`os.environ` object
      *can not* be replaced by another object, that is why we change its
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

  def on_context_leave(self):
    ''' Called when the context manager entered with
    :func:`magic.enter_context` is exited. Undos all of the stuff
    that :meth:`on_context_enter` did and more.

    * Stop the Craftr Runtime Server if it was started
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

  *New in v1.1.0*:
  A target object can also represent a Python function as a target
  in the Ninja manifest. This is called an RTS task. Use the
  :func:`task` function to create tasks or pass a function for the
  *command* parameter of the :class:`Target` constructor. The
  function must accept no parameters if :attr:`inputs` and :attr:`outputs`
  are **both** :const:`None` or accept these two values as parameters.

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

    This attribute can also be None.

  .. attribute:: outputs

    A list of filenames that are listed as outputs of the target and
    that are substituted for ``$out`` during the Ninja execution.
    Can be None. The :class:`Target` constructor accepts a list of
    filenames or a single filename for this attribute.

    This attribute can also be None.

  .. attribute:: implicit_deps

    A list of filenames that are required to build the Target,
    additionally to the :attr:`inputs`, but are not expanded by
    the ``$in`` variable in Ninja. See "Implicit dependencies"
    in the `Ninja Manual`_.

  .. attribute:: order_only_deps

    See "Order-only dependencies" in the `Ninja Manual`_.

  .. attribute:: requires

    A list of targets that are to be built before this target is.
    This is useful for speciying task dependencies that don't have
    input and/or output files.

    The constructor accepts None, a :class:`Target` object or a
    list of targets and will convert it to a list of targets.

    .. code-block:: python

      @task
      def hello():
        info("Hello!")

      @task(requires = [hello])
      def ask_name():
        info("What's your name?")

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

  .. attribute:: meta

    A dictionary of meta variables that can be set from anywhere. Usually,
    rule functions use this dictionary to promote additional information
    to the caller, for example what the actual computed output filename
    of a compilation is.

  .. attribute:: graph

    Initially None. After :func:`finalize` is called, this is a
    namedtuple of :class:`Graph` which has input and output sets
    of targets of the dependencies in the Target.

  .. automethod:: Target.__lshift__

  .. _Ninja Manual: https://ninja-build.org/manual.html
  '''

  Graph = collections.namedtuple('Graph', 'inputs outputs') #: Type for :attr:`Target.graph`
  RTS_None = 'none'   #: The target and its dependencies are plain command-line targets
  RTS_Mixed = 'mixd'  #: The target and/or its dependencies are a mix of command-line targets and tasks
  RTS_Plain = 'plain' #: The target and all its dependencies are plain task targets

  def __init__(self, command, inputs=None, outputs=None, implicit_deps=None,
      order_only_deps=None, requires=None, foreach=False, description=None,
      pool=None, var=None, deps=None, depfile=None, msvc_deps_prefix=None,
      explicit=False, frameworks=None, meta=None, module=None, name=None):

    if callable(command):
      # This target will be a task, alias RTS target.
      if not name:
        name = command.__name__
      if not description:
        description = command.__doc__
    elif isinstance(command, str):
      command = shell.split(command)
    else:
      command = _check_list_of_str('command', command)
    if not command:
      raise ValueError('command can not be empty')

    if not module and craftr.module:
      module = craftr.module()
    if not name:
      name = Target._get_name(module)

    if requires is not None:
      if isinstance(requires, Target):
        requires = [requires]
      else:
        requires = list(requires)
        for obj in requires:
          if not isinstance(obj, Target):
            raise TypeError('requires must contain only Target objects')

    def _expand(x, name):
      if x is None: return None
      if isinstance(x, str):
        x = [x]
      x = expand_inputs(x)
      x = _check_list_of_str(name, x)
      return x

    inputs = _expand(inputs, 'inputs')
    outputs = _expand(outputs, 'outputs')
    implicit_deps = _expand(implicit_deps, 'implicit_deps')
    order_only_deps = _expand(order_only_deps, 'order_only_deps')

    if foreach and len(inputs) != len(outputs):
      raise ValueError('len(inputs) must match len(outputs) in foreach Target')

    if meta is None:
      meta = {}
    if not isinstance(meta, dict):
      raise TypeError('meta must be a dictionary')

    self.module = module
    self.name = name

    self.rts_func = None
    if callable(command):
      self.rts_func = command
      command = [RTS_COMMAND, self.fullname]

    self.command = command
    self.inputs = inputs
    self.outputs = outputs
    self.implicit_deps = implicit_deps or []
    self.order_only_deps = order_only_deps or []
    self.requires = requires or []
    self.foreach = foreach
    self.pool = pool
    self.description = description
    self.deps = deps
    self.depfile = depfile
    self.msvc_deps_prefix = msvc_deps_prefix
    self.frameworks = expand_frameworks(frameworks or [])
    self.explicit = explicit
    self.meta = meta
    self.graph = None

    if module:
      module.__session__.register_target(self)

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

  @property
  def finalized(self):
    return self.graph is not None

  def execute_task(self, exec_state=None):
    ''' Execute the :attr:`rts_func` of the target. This calls the
    function with the inputs and outputs of the target (if any of
    these are not None) or with no arguments (if both is None).

    This function catches all exceptions that the wrapped function
    might raise and prints the traceback to stdout and raises a
    :class:`TaskError` with status-code 1.

    :param exec_state: If this parameter is not None, it must be
      a dictionary where the task can check if it already executed.
      Also, inputs of this target will be executed if the parameter
      is a dictionary.
    :raise RuntimeError: If the target is not an RTS task.
    :raise TaskError: If this task (or any of the dependent tasks,
      only if *exec_state* is not None) exits with a not-None,
      non-zero exit code. '''

    if not self.rts_func:
      raise RuntimeError('target is not an RTS task: {!r}'.format(self.fullname))
    if exec_state is not None and exec_state.get(self.fullname):
      return  # already executed
    if exec_state is not None:
      exec_state[self.fullname] = True
      for dep in self.graph.inputs:
        dep.execute_task(exec_state)
    try:
      with magic.enter_context(craftr.module, self.module):
        if self.inputs is None and self.outputs is None:
          result = self.rts_func()
        else:
          result = self.rts_func(self.inputs, self.outputs)
    except BaseException as exc:
      traceback.print_exc()
      raise TaskError(self, 1) from None

    if result is not None and result != 0:
      raise TaskError(self, result)

  def finalize(self, session):
    ''' Gather the inputs and outputs of the target and create a
    new :class:`Graph` to fill the :attr:`graph` attribute. '''

    if self.finalized:
      raise RuntimeError('target already finalized: {!r}'.format(self.fullname))
    self.graph = Target.Graph(set(), set())
    for fn in self.inputs or ():
      dep = session.find_target_for_file(fn)
      if dep: self.graph.inputs.add(dep)
    for fn in self.outputs or ():
      dep = session.find_target_for_file(fn)
      if dep: self.graph.outputs.add(dep)
    self.graph.inputs.update(self.requires)

  def get_rts_mode(self):
    ''' Returns the RTS information for this target:

    * :data:`RTS_None` if this target and none of its dependencies
    * :data:`RTS_Plain` if this target and all of its dependencies are tasks
    * :data:`RTS_Mixed` if this target or any of its dependencies are tasks
      but there is at least one normal target '''

    if not self.finalized:
      raise RuntimeError('not finalized')
    mode = self.RTS_Plain if self.rts_func else self.RTS_None
    for dep in self.graph.inputs:
      dep_mode = dep.get_rts_mode()
      if dep_mode == self.RTS_Mixed or dep_mode != mode:
        mode = self.RTS_Mixed
    return mode


class TargetBuilder(object):
  ''' This is a helper class to make it easy to implement rule functions
  that create a :class:`Target`. Rule functions usually depend on inputs
  (being files or other Targets that can also contain additional frameworks),
  rule-level settings and :class:`Frameworks<Framework>`. The TargetBuilder
  takes all of this into account and prepares the data conveniently.

  The following example shows how to make a simple rule function that
  compiles C/C++ source files into object files with GCC. The actual
  compiler name can be overwritten and additional flags can be specified
  by passing them directly to the rule function or via frameworks
  (accumulative).

  .. code:: python

    #craftr_module(test)

    from craftr import TargetBuilder, Framework, path
    from craftr.ext import platform
    from craftr.ext.compiler import gen_output

    def compile(sources, frameworks=(), **kwargs):
      """
      Simple rule to compile a number of source files into an
      object files using GCC.
      """

      builder = TargetBuilder(sources, frameworks, kwargs)
      outputs = gen_output(builder.inputs, suffix = platform.obj)
      command = [builder.get('program', 'gcc'), '-c', '$in', '-o', '$out']
      command += builder.merge('additional_flags')
      return builder.create_target(command, outputs = outputs)

    copts = Framework(
      additional_flags = ['-pedantic', '-Wall'],
    )

    objects = compile(
      sources = path.glob('src/**/*.c'),
      frameworks = [copts],
      additional_flags = ['-std=c11'],
    )

  :param inputs: Inputs for the target. Processed by :func:`expand_inputs`,
    the resulting frameworks are then processed by :func:`expand_frameworks`.
    The expanded inputs are saved in the :attr:`inputs` attribute of the
    :class:`TargetBuilder`. Use this attribute instead of the original value
    passed to this parameter! It is guaruanteed to be a list of filenames
    only.
  :param frameworks: A list of frameworks to take into account additionally.
  :param kwargs: Additional options that will be turned into their own
    :class:`Framework` object, but it will *not* be passed to the Target
    that is created with :meth:`create_target` as these options should not
    be inherited by rules that will receive the target as input.
  :param module: Override the module that will receive the target.
  :param name: Override the target name. If not specified, the target
    name is retrieved using Craftr's target name deduction from the name
    the target is assigned to.
  :param stacklevel: The stacklevel which the calling rule function is at.
    This defaults to 1, which is fine for rule functions that directly
    create the :class:`TargetBuilder`.

  .. attribute:: caller

    Name of the calling function.

    .. code:: python

      def my_rule(*args, **kwargs):
        builder = TargetBuilder(None)
        assert builder.caller == 'my_rule'

  .. attribute:: inputs

    :const:`None` or a pure list of filenames that have been passed
    via the *inputs* parameter of the TargetBuilder.

  .. attribute:: frameworks

    A list of frameworks compiled from the frameworks of :class:`Target`
    objects in the *inputs* parameter of the constructor and the frameworks
    that have been specified directly with the *frameworks* parameter.

  .. attribute:: kwargs

    The additional options that have been passed with the *kwargs* argument.
    These are turned into their own :class:`Framework` which is only taken
    into account for the :attr:`options` but it is not passed to the
    :class:`Target`  created with :meth:`create_target`.

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

  .. attribute:: meta

    Meta data for the Target that is passed directly to
    :attr:`Target.meta`.

  .. automethod:: TargetBuilder.__getitem__
  '''

  def __init__(self, inputs, frameworks=(), kwargs=None, meta=None,
      module=None, name=None, stacklevel=1):
    if kwargs is None:
      kwargs = {}
    if meta is None:
      meta = {}
    if not isinstance(meta, dict):
      raise TypeError('meta must be a dictionary')
    self.meta = meta
    self.caller = magic.get_caller(stacklevel + 1)
    frameworks = list(frameworks)

    if inputs is not None:
      inputs = expand_inputs(inputs, frameworks)
    self.inputs = inputs
    self.frameworks = expand_frameworks(frameworks)
    self.kwargs = kwargs
    self.options = FrameworkJoin(Framework(self.caller, kwargs), *self.frameworks)
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
          if self.module.project_name + '.' + name not in session.targets:
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
    ''' Alias for :meth:`FrameworkJoin.__getitem__` on the :attr:`options`. '''

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
      meta=self.meta, module=self.module, name=self.name, **kwargs)
    for key, value in self.target_attrs.items():
      # We can only set attributes that the target already has.
      getattr(target, key)
      setattr(target, key, value)
    return target

  def write_command_file(self, arguments, suffix=None, always=False):
    ''' Writes a file to the :data:`CMDDIR` folder in the build directory
    (ie. the current directory) that contains the command-line arguments
    specified in *arguments*. The name of that file is the name of the
    Target that is created with this builder. Optionally, a suffix
    for that file can be specified to be able to write multiple such
    files. Returns the filename of the generated file. If *always* is
    set to True, the file will always be created even if `Session.export`
    is set to False. '''

    filename = path.join(CMDDIR, self.fullname)
    if suffix:
      filename += suffix
    if not always and not session.export:
      return filename

    path.makedirs(CMDDIR)
    with open(filename, 'w') as fp:
      for arg in arguments:
        fp.write(shell.quote(arg))
        fp.write(' ')

    return filename

  def write_multicommand_file(self, commands, cwd = None, exit_on_error = True,
      suffix = None, always = False):
    ''' Write a platform dependent script that executes the specified
    *commands* in order. If *exit_on_error* is True, the script will
    exit if an error is encountered while executing the commands.

    Returns a list representing the command-line to run the script.

    :param commands: A list of strings or command lists that are
      written into the script file.
    :param cwd: Optionally, the working directory to change to
      when the script is executed.
    :param exit_on_error: If this is True, the script will exit
      immediately if any command returned a non-zero exit code.
    :param suffix: An optional file suffix. Note that on Windows,
      ``.cmd`` is added to the filename after that suffix.
    :param always: If this is true, the file is always created, not
      only if a Ninja manifest is being exported (see :attr:`Session.export`).
    :return: A tuple of two elements. The first element is a command list
      that represents the command used to invoke the created script. The
      second element is the actual command file that was written.
    '''

    from craftr.ext import platform

    filename = path.join(CMDDIR, self.fullname)
    if suffix:
      filename += suffix
    filename = path.normpath(filename, abs=False)

    if platform.name == platform.WIN32:
      filename += '.cmd'
      result = ['cmd', '/Q', '/c', filename]
    else:
      result = [filename]

    if always or session.export:
      # Make sure we only have strings of commands.
      prep_commands = []
      for command in commands:
        if not isinstance(command, str):
          command = ' '.join(map(shell.quote, command))
        prep_commands.append(command)
      commands = prep_commands

      # Write the script file.
      path.makedirs(CMDDIR)
      with open(filename, 'w') as fp:
        if platform.name == platform.WIN32:
          if cwd:
            fp.write('cd ' + shell.quote(cwd) + '\n\n')
          for cmd in commands:
            # XXX For some reason, we need to invoke these commands
            # using "cmd /Q /c" too instead of just the command, otherwise
            # there seem to be some problems for example with CMake which
            # causes the bash script to exit immediately after CMake
            # is finished.
            fp.write('cmd /Q /c ' + cmd)
            fp.write('\n')
            fp.write('if %errorlevel% neq 0 exit %errorlevel%\n\n')
        else:
          # XXX Are there differences from bash to other shells we need to
          # take into account?
          fp.write('#!' + utils.find_program(environ['SHELL']) + '\n')
          fp.write('set -e\n')
          if cwd:
            fp.write('cd ' + shell.quote(cwd) + '\n')
          fp.write('\n')
          for cmd in commands:
            fp.write(cmd)
            fp.write('\n')
      os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
        stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)  # rwxrw-r--

    return result, filename


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

  .. note::

    The :class:`FrameworkJoin` does not use :func:`expand_frameworks` but
    uses the list of frameworks passed to the constructor as-is.

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


class TaskError(Exception):
  ''' Raised from :meth:`Target.execute_task()`. '''

  def __init__(self, task, result):
    self.task = task
    self.result = result

  def __str__(self):
    return 'task {!r} returned with result code {!r}'.format(
      self.task.fullname, self.result)


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
  frameworks of all input :class:`Target` objects will be appended. The
  frameworks need to be expanded with :func:`expand_frameworks`. '''

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


def expand_frameworks(frameworks, result=None):
  ''' Given a list of :class:`Framework` objects, this function creates
  a new list that contains all objects of *frameworks* and additionally
  all objects that are listed in each of the frameworks ``"frameworks"``
  key recursively. Duplicates are also elimated. '''

  if result is None:
    result = []
  for fw in frameworks:
    # xxx: does this compare the dictionary contents? We do NOT want that.
    if fw not in result:
      result.append(fw)
    expand_frameworks(fw.get('frameworks', []), result)
  return result


def task(func=None, *args, **kwargs):
  ''' Create a task :class:`Target` that uses the Craftr RTS
  feature. If *func* is None, this function returns a decorator
  that finally creates the :class:`Target`, otherwise the task
  is created instantly.

  The wrapped function must either

  * take no parameters, this is when both the *inputs* and
    *outputs* of the task are :const:`None`, or
  * take two parameters being the *inputs* and *outputs* of the
    task

  .. code-block:: python

    @task
    def hello():  # note: no parameters
      info("Hello, World!")

    @task(inputs = another_target, outputs = 'some/output/file')
    def make_some_output_file(inputs, outputs):  # note: two parameters!
      # ...

    yat = task(some_function, inputs = yet_another_target,
               name = 'yet_another_task')

  .. important::

    Be aware that tasks executed through Ninja (and thus via RTS)
    are executed in a seperate thread!

  Note that unlike normal targets, a task is explicit by default,
  meaning that it must explicitly be specified on the command line
  or be required as an input to another target to be executed.

  :param func: The callable function to create the RTS target
    with or None if you want to use this function as a decorator.
  :param args: Additional args for the :class:`Target` constructor.
  :param kwargs: Additional kwargs for the :class:`Target` constructor.
  :return: :class:`Target` or a decorator that returns :class:`Target`
  '''

  kwargs.setdefault('explicit', True)

  def wrapper(func):
    return Target(func, *args, **kwargs)

  if func is None:
    return wrapper
  if not callable(func):
    raise TypeError('func must be callable')
  return wrapper(func)


def import_file(filename):
  ''' Import a Craftr module by filename. The Craftr module identifier
  must be determinable from this file either by its ``#craftr_module(..)``
  identifier or filename. '''

  if not path.isabs(filename):
    filename = path.local(filename)
  return session.ext_importer.import_file(filename)


def import_module(modname, globals=None, fromlist=None):
  ''' Similar to :func:`importlib.import_module()`, but this function can
  also imports contents of *modname* into *globals*. If *globals* is
  specified, the module will be directly imported into the dictionary.
  If *fromlist* list is ``*``, a wildcard import into *globals* will be
  performed, otherwise *fromlist* must be :class:`None` or a list of
  names to import.

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


def memoize_tool(func):
  ''' Decorator for functions that take the path to a program as an
  argument and extract information from it such as its version or
  raising a :class:`craftr.ext.compiler.ToolDetectionError` if the
  tool could not be detected.

  Basically, this is just a memoize decorator but it applies
  :func:`path.normpath` to the argument passed to the wrapped
  function. :-) '''

  cache = {}

  @functools.wraps(func)
  def wrapper(program):
    program = path.normpath(program, abs=False)
    try:
      result = cache[program]
    except KeyError:
      result = cache[program] = func(program)
    return result

  return wrapper


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
from craftr import ext, options, path, shell, ninja, rts, utils

__all__ = ['session', 'module', 'path', 'options', 'shell', 'utils', 'environ',
  'Target', 'TargetBuilder', 'Framework', 'FrameworkJoin',
  'debug', 'info', 'warn', 'error', 'return_', 'expand_inputs', 'task',
  'import_file', 'import_module', 'memoize_tool', 'craftr_min_version']

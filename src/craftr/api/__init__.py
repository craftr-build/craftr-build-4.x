# -*- coding: utf8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2018  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This module implements the API for the Craftr build scripts.

Craftr build scripts are plain Python scripts that import the members of
this module to generate a build graph. The functions in this module are based
on a global thread local that binds the current build graph master, target,
etc. so they do not have to be explicitly declared and passed around.
"""

__all__ = [
  'session',
  'OS',
  'BUILD',
  'BuildSet',
  'current_session',
  'current_scope',
  'current_target',
  'current_operator',
  'bind_target',
  'bind_operator'
]

import collections
import contextlib
import json
import nodepy
import nr.fs
import os
import sys
import toml

from craftr.core import build as _build
from nodepy.utils import pathlib
from nr.stream import stream
from nr.types.named import Named
from nr.types.map import MapAsObject
from nr.types.set import OrderedSet
from werkzeug.local import LocalProxy
from .modules import CraftrModuleLoader
from .proplib import PropertySet, Properties, NoSuchProperty

STDLIB_DIR = nr.fs.join(nr.fs.dir(nr.fs.dir(nr.fs.dir(__file__))))

session = None  # The current #Session
OS = LocalProxy(lambda: session.os_info)
BUILD = LocalProxy(lambda: session.build_info)


class OsInfo(Named):
  name: str
  id: str
  type: str
  arch: str

  @classmethod
  def new(cls):
    if sys.platform.startswith('win32'):
      return cls('windows', 'win32', os.name, 'x86_64' if os.environ.get('ProgramFiles(x86)') else 'x86')
    elif sys.platform.startswith('darwin'):
      return cls('macos', 'darwin', 'posix', 'x86_64' if sys.maxsize > 2**32 else 'x86')
    elif sys.platform.startswith('linux'):
      return cls('linux', 'linux', 'posix', 'x86_64' if sys.maxsize > 2**32 else 'x86')
    else:
      raise EnvironmentError('(yet) unsupported platform: {}'.format(sys.platform))


class BuildInfo(Named):
  variant: str

  @property
  def debug(self):
    return self.variant == 'debug'

  @property
  def release(self):
    return self.variant == 'release'


class Session(_build.Master):
  """
  This is the root instance for a build session. It introduces a new virtual
  entity called a "scope" that is created for every build script. Target names
  will be prepended by that scope, relative paths are treated relative to the
  scopes current directory and every scope gets its own build output directory.
  """

  def __init__(self, build_root: str, build_directory: str, build_variant: str):
    super().__init__()
    self._build_root = nr.fs.canonical(build_root)
    self._build_directory = nr.fs.canonical(build_directory)
    self._build_variant = build_variant
    self._current_scopes = []
    self.options = {}
    self.loader = CraftrModuleLoader(self)
    self.nodepy_context = nodepy.context.Context()
    self.nodepy_context.resolver.loaders.append(self.loader)
    self.nodepy_context.resolver.paths.append(pathlib.Path(STDLIB_DIR))
    self.target_props = PropertySet()
    self.dependency_props = PropertySet()
    self.os_info = OsInfo.new()
    self.build_info = BuildInfo(self._build_variant)

  def load_config(self, config):
    """
    Loads a TOML configuration. Evaluates `if(...)` expressions in the keys
    of the configuration. Such conditional expressions must be of the form
    `DATA=VALUE` where `DATA` can be a Python expressions that usually reads
    a member of the #OS or #BUILD objects and `VALUE` is treated as a string
    without the need to add quotes.

    Example:

    ```toml
    ['if(OS.id==win32)'.'craftr/lang/cxx']
    staticRuntime = true
    ```

    The configuration can also be represented as JSON:

    ```json
    {
      "if(OS.id=win32)": {
        "craftr/libs/opencl": {
          "vendor": "nvidia"
        }
      }
    }
    ```
    """

    if isinstance(config, str):
      with open(config) as fp:
        if path.getsuffix(config) == 'json':
          config = json.load(fp)
        else:
          config = toml.load(fp)

    def handle_key(key, data):
      if key.startswith('if(') and key.endswith(')'):
        left, right = key[3:-1].partition('=')[::2]
        expr = 'str({}) == {!r}'.format(left, right.strip())
        # TODO: Catch exception?
        result = eval(expr, {'OS': self.os_info, 'BUILD': self.build_info})
        if not result: return
        for key, value in data.items():
          handle_key(key, value)
      else:
        for sub_key, value in data.items():
          self.options[key + ':' + sub_key] = value

    for key, value in config.items():
      handle_key(key, value)

  def load_module(self, name):
    return self.nodepy_context.require(name + '.craftr', exports=False)

  def load_module_from_file(self, filename, is_main=False):
    filename = pathlib.Path(nr.fs.canonical(filename))
    module = self.loader.load_module(self.nodepy_context, None, filename)
    module.is_main = is_main
    self.nodepy_context.register_module(module)
    self.nodepy_context.load_module(module)
    return module

  @property
  def build_root(self):
    return self._build_root

  @property
  def build_directory(self):
    return self._build_directory

  @property
  def build_variant(self):
    return self._build_variant

  @contextlib.contextmanager
  def enter_scope(self, name, version, directory):
    scope = Scope(self, name, version, directory)
    self._current_scopes.append(scope)
    try: yield scope
    finally:
      assert self._current_scopes.pop() is scope

  @property
  def current_scope(self):
    return self._current_scopes[-1] if self._current_scopes else None

  @property
  def current_target(self):
    if self._current_scopes:
      return self._current_scopes[-1].current_target
    return None


class Scope(nr.interface.Implementation):
  """
  A scope basically represents a Craftr build module. The name of a scope is
  usually determined by the Craftr module loader.

  Note that a scope may be created with a name and version set to #None. The
  scope must be initialized with the #module_id() build script function.
  """

  nr.interface.implements(proplib.Path.OwnerInterface)

  def __init__(self, session: Session, name: str, version: str, directory: str):
    self.session = session
    self.name = name
    self.version = version
    self.directory = directory
    self.current_target = None

  @property
  def build_directory(self):
    return nr.fs.join(self.session.build_directory, self.name)

  @nr.interface.override
  def path_get_parent_dir(self):
    return self.directory


class Target(_build.Target):
  """
  Extends the graph target class by a property that describes the active
  build set that is supposed to be used by the next function that creates an
  operator.
  """

  class Dependency:
    def __init__(self, target, public):
      self.target = target
      self.public = public
      self.properties = Properties(session.dependency_props, owner=current_scope())
    def __getitem__(self, key):
      return self.properties[key]

  def __init__(self, name: str, scope:Scope):
    super().__init__(session, '{}@{}'.format(scope.name, name))
    self.name = name
    self.scope = scope
    self.current_operator = None
    self.properties = Properties(session.target_props, owner=current_scope())
    self.public_properties = Properties(session.target_props, owner=current_scope())
    self._dependencies = []
    self._operator_name_counter = collections.defaultdict(lambda: 1)

  def __getitem__(self, prop_name):
    """
    Read a (combined) property value from the target.
    """

    prop = self.properties.propset[prop_name]
    inherit = prop.options.get('inherit', False)
    return self.get_prop(prop_name, inherit=inherit)

  @property
  def build_directory(self):
    return nr.fs.join(self.scope.build_directory, self.name)

  @property
  def dependencies(self):
    return list(self._dependencies)

  def add_dependency(self, target: 'Target', public: bool):
    """
    Adds another target as a dependency to this target. This will cause public
    properties to be inherited when using the #prop() method.
    """

    if not isinstance(target, Target):
      raise TypeError('expected Target, got {}'.format(
        type(target).__name__))

    for x in self._dependencies:
      if x.target is target:
        raise RuntimeError('dependency to "{}" already exists'.format(target.id))
    dep = Target.Dependency(target, public)
    self._dependencies.append(dep)
    return dep

  def get_prop(self, prop_name, inherit=False, default=NotImplemented):
    """
    Returns a property value. If a value exists in #exported_props and #props,
    the #exported_props takes preference.

    If *inherit* is #True, the property must be a #proplib.List property
    and the values in the exported and non-exported property containers as
    well as transitive dependencies are respected.

    Note that this method does not take property options into account, so
    even if you specified `options={'inherit': True}` on the property you
    want to retrieve, you will need to pass `inherit=True` explicitly to this
    method. If you want this to happen automatically, use the #__getitem__().
    """

    if inherit:
      def iter_values():
        yield self.public_properties[prop_name]
        yield self.properties[prop_name]
        for target in self.transitive_dependencies().attr('target'):
          yield target.public_properties[prop_name]
      prop = self.properties.propset[prop_name]
      return prop.type.inherit(prop_name, iter_values())
    else:
      if self.public_properties.is_set(prop_name):
        return self.public_properties[prop_name]
      elif self.properties.is_set(prop_name):
        return self.properties[prop_name]
      elif default is NotImplemented:
        return self.properties.propset[prop_name].get_default()
      else:
        return default

  def get_props(self, prefix='', as_object=False):
    """
    Creates a dictionary from all property values in the Target that start
    with the specified *prefix*. If *as_object* is #True, an object that wraps
    the dictionary will be returned instead. Modifying the returned dictionary
    does not have an effect on the actualy property values of the Target.

    The prefix will be stripped from the keys (or attributes) of the returned
    dictionary (or object).

    # Parameters
    prefix (str): The prefix to filter properties.
    as_object (bool): Return an object instead of a dictionary.
    return (dict, MapAsObject)
    """

    result = {}
    propset = self.properties.propset
    for prop in filter(lambda x: x.name.startswith(prefix), propset.values()):
      result[prop.name[len(prefix):]] = self[prop.name]
    if as_object:
      result = MapAsObject(result)
    return result

  def transitive_dependencies(self):
    """
    Returns an iterator that yields the #Dependency objects of this target
    and all of their (public) transitive dependencies. The returned iterator
    is a #stream instance, thus you can use any streaming operations on the
    returned object.
    """

    def worker(target, private=False):
      for dep in target.dependencies:
        if dep.public or private:
          yield dep
        yield from worker(dep.target)
    return stream.unique(worker(self, private=True))


class Operator(_build.Operator):
  """
  Extends the graph operator class so that the build master does not need
  to be passed explicitly.
  """

  def __init__(self, *args, **kwargs):
    super().__init__(session, *args, **kwargs)


class BuildSet(_build.BuildSet):

  def __init__(self, inputs, outputs, variables=None, *args, **kwargs):
    super().__init__(session, *args, **kwargs)
    self.variables.update(variables or {})
    for set_name, files in inputs.items():
      if isinstance(files, str):
        files = [files]
      self.add_input_files(set_name, files)
    for set_name, files in outputs.items():
      if isinstance(files, str):
        files = [files]
      self.add_output_files(set_name, files)


class ModuleError(RuntimeError):

  def __init__(self, scope_name, message):
    self.scope_name = scope_name
    self.message = message

  def __str__(self):
    return '{}: {}'.format(self.scope_name, self.message)


def current_session(do_raise=True):
  if do_raise and session is None:
    raise RuntimeError('no current session')
  return session


def current_scope(do_raise=True):
  scope = session.current_scope
  if do_raise and scope is None:
    raise RuntimeError('no current scope')
  if not scope.name or not scope.version:
    raise RuntimeError('current scope has no name/version, use '
                       'project() function to initialize')
  return scope


def current_target(do_raise=True):
  scope = current_scope(do_raise)
  target = scope and scope.current_target
  if do_raise and target is None:
    raise RuntimeError('no current target')
  return target


def current_operator(do_raise=True):
  target = current_target(do_raise)
  operator = target and target.current_operator
  if do_raise and operator is None:
    raise RuntimeError('no current operator')
  return operator


def bind_target(target):
  """
  Binds the specified *target* as the current target in the current scope.
  """

  session.current_scope.current_target = target


def bind_operator(operator):
  """
  Binds the specified *build_set* in the currently active target.
  """

  current_target().current_operator = operator


# Public API Level 1 (Build Scripts)
# ==================================

__all__ += [
  'project',
  'config',
  'target',
  'depends',
  'properties',
  'operator',
  'build_set'
]


def project(name, version):
  scope = session.current_scope
  scope.name = name
  scope.version = version


def config(toml_str):
  """
  Pass a TOML formatted string that will update the session's configuration.
  """

  session.options.update(toml.loads(toml_str))


def target(name, bind=True):
  """
  Create a new target with the specified *name* in the current scope and
  set it as the current target.
  """

  scope = current_scope()
  target = session.add_target(Target(name, scope))
  if bind:
    bind_target(target)
  return target


def depends(target, public=False):
  """
  Add *target* as a dependency to the current target.

  target (str, Target, List[Union[Target, str]])
  """

  if isinstance(target, str):
    scope, name = target.partition(':')[::2]
    if not scope:
      scope = current_scope().name
    try:
      target = session.targets[scope + '@' + name]
    except KeyError as exc:
      session.load_module(scope)
      target = session.targets[scope + '@' + name]
  elif isinstance(target, (list, tuple)):
    [depends(x) for x in target]
  else:
    return current_target().add_dependency(target, public)


def properties(_scope=None, _props=None, _target=None, **kwarg_props):
  """
  Sets properties in the current target.

  _scope (str): A scope prefix. If specified, it will be prefixed to
      both *_props* and *kwarg_props*. If it is a dictionary instead
      of a string, it will behave as the *_props* argument.
  _props (dict): A dictionary of properties to set. The keys in the
      dictionary can have special syntax to mark a property as publicly
      visible (prefix with `@`) and/or to append to existing values in
      the same target (suffix with `+`).
  _target (Target): The target to set the properties in. Defaults to
      the currently active target.
  kwarg_props: Keyword-argument style property values. Similar to the
      *_props* dictionary, keys in this dictionary may be prefixed with
      `public__` and/or suffixed with `__append`.
  """

  target = _target or current_target()
  props = {}

  if isinstance(_scope, dict):
    _props = _scope
    _scope = ''
  else:
    _scope += '.'

  # Prepare the parameters from both sources.
  for key, value in (_props or {}).items():
    public = append = False
    while True:
      if not public and key[0] == '@': public, key = True, key[1:]
      elif not append and key[0] == '+': append, key = True, key[1:]
      elif not append and key[-1] == '+': append, key = True, key[:-1]
      else: break
    props.setdefault(key, []).append((value, public, append))
  for key, value in kwarg_props.items():
    public = key.startswith('public__')
    if public: key = key[8:]
    append = key.endswith('__append')
    if append: key = key[:-8]
    props.setdefault(key, []).append((value, public, append))

  for key, operations in props.items():
    key = _scope + key
    for value, public, append in operations:
      dest = target.public_properties if public else target.properties
      if append and dest.is_set(key):
        prop = dest.propset[key]
        value = prop.coerce(value, dest.owner)
        value = dest.propset[key].type.inherit(key, [dest[key], value])
      try:
        dest[key] = value
      except NoSuchProperty as exc:
        print('[WARNING]: Property {} does not exist'.format(exc)) # TODO


def operator(name, commands, variables=None, target=None, bind=None, **kwargs):
  """
  Creates a new #Operator in the current target and returns it. This is not
  usually called from a project build script but modules that implement new
  target types.

  The *name* of the operator will be adjusted to contain a counting index
  to prevent operator name clashes.

  If *target* is specified, the function is assumed to be used independently
  from the current target's context and is therefore not bound to the current
  target or the specified one.
  """

  if target is None:
    target = current_target()
    if bind is None: bind = True
  else:
    if bind is None: bind = False

  if not isinstance(commands, _build.Commands):
    commands = _build.Commands(commands)

  if '#' not in name:
    count = target._operator_name_counter[name]
    target._operator_name_counter[name] = count + 1
    name += '#' + str(count)

  op = target.add_operator(Operator(name, commands, **kwargs))
  op.variables.update(variables or {})
  bind_operator(op)
  return op


def build_set(*args, operator=None, **kwargs):
  """
  Creates a new build set in the current operator adding the files specified
  in the *inputs* and *outputs* dictionaries.
  """

  if operator is None:
    operator = current_operator()

  bset = BuildSet(*args, **kwargs)
  operator.add_build_set(bset)
  return bset


# Utilities
# =========

__all__ += [
  'path',
  'complete_list_with',
  'glob',
  'chfdir',
  'fmt',
  'error'
]

path = nr.fs

def complete_list_with(dest, source, update):
  """
  Calls *update()* for every missing element in *dest* compared to *source*.
  The update function will receive the respective element from *source* as
  an argument.

  Modifies and returns *dest*.
  """

  if len(dest) >= len(source): return dest
  while len(dest) < len(source):
    dest.append(update(source[len(dest)]))
  return dest


def glob(patterns, parent=None, excludes=None, include_dotfiles=False,
         ignore_false_excludes=False):
  if not parent:
    parent = session.current_scope.directory
  return nr.fs.glob(patterns, parent, excludes, include_dotfiles,
                    ignore_false_excludes)


def chfdir(filename):
  if nr.fs.isabs(filename):
    filename = nr.fs.rel(filename, current_scope().directory)
  return nr.fs.join(current_scope().build_directory, filename)


def fmt(s, frame=None):
  """
  Formats the string *s* with the variables from the parent frame or the
  specified frame-object *frame*.
  """

  import inspect
  import gc
  import types

  class Resolver:
    def __init__(self, frame):
      self.frame = frame
      self._func = NotImplemented
    @property
    def func(self):
      if self._func is NotImplemented:
        self._func = next(filter(lambda x: isinstance(x, types.FunctionType),
            gc.get_referrers(self.frame.f_code)), None)
      return self._func
    def __getitem__(self, key):
      # Try locals
      try: return self.frame.f_locals[key]
      except KeyError: pass
      # Try non-locals
      try:
        index = self.frame.f_code.co_freevars.index(key)
      except ValueError:
        pass
      else:
        if self.func:
          x = self.func.__closure__[index]
          return x
      # Try globals
      g = self.frame.f_globals
      g = g.get('__dict__', g)
      try: return g[key]
      except KeyError: pass
      raise KeyError(key)

  frame = frame or inspect.currentframe().f_back
  vars = Resolver(frame)
  return s.format_map(vars)


def error(*message):
  """
  Raises a #ModuleError.
  """

  raise ModuleError(current_scope().name, ' '.join(map(str, message)))

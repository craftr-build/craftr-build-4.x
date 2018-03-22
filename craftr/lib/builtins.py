# This file is loaded by the craftr.main.Context where the `context`
# variable is available.

try:
  context
except NameError:
  raise RuntimeError('this file should not be imported')

__all__ = ['BUILD', 'OS', 'error', 'fmt', 'glob', 'load', 'option_default']

import collections
import os
import platform
import sys
import types
from nr import path
from nr.datastructures.chaindict import ChainDict
from nr.datastructures.objectfrommapping import ObjectFromMapping
from craftr import core, dsl

OsInfo = collections.namedtuple('OsInfo', 'name id type arch')


class BuildInfo(collections.namedtuple('_BuildInfo', 'variant')):

  @property
  def debug(self):
    return self.variant == 'debug'

  @property
  def release(self):
    return self.variant == 'release'


def get_call_context(stackdepth=1, dependency=True, target=True, module=True):
  """
  Returns the #core.Module, #core.Target or #core.Dependency from the
  parent stackframe. Raises a #RuntimeError if it can not be determined.
  """

  f= sys._getframe(stackdepth+1)
  scope = sys._getframe(stackdepth+1).f_globals
  if '__dict__' in scope:
    # For code evaluated with nr.ast.dynamic_eval().
    scope = scope['__dict__']
  if dependency and isinstance(scope.get('self'), core.Dependency):
    return scope['dependency']
  elif target and isinstance(scope.get('target'), core.Target):
    return scope['target']
  elif module and isinstance(scope.get('module'), core.Module):
    return scope['module']
  print(scope['module'], scope.get('module'))
  raise RuntimeError('Call context could not be determined')


def error(*message):
  raise dsl.ExplicitRunError(' '.join(map(str, message)))


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
      try: return self.frame.f_globals[key]
      except KeyError: pass

  frame = frame or inspect.currentframe().f_back
  vars = Resolver(frame)
  return s.format_map(vars)


def glob(patterns, parent=None, excludes=None):
  if not parent:
    obj = get_call_context(dependency=False)
    parent = obj.directory
  return path.glob(patterns, parent, excludes)


def load(name):
  """
  Similar to the `load` statement in the Craftr build file, but it can be
  used to load a Python script into a new namespace (not the build scripts
  eval namespace).

  Can also be used to load another Craftr build script (if no relative or
  absolute filename is specified). Will return the module's eval namespace.
  """

  if name.startswith('./') or name.startswith('.\\') \
      or path.isabs(name):
    ns = types.ModuleType(name)
    parent_globals = sys._getframe(1).f_globals
    name = path.canonical(name, path.dir(parent_globals['__file__']))

    # Make sure the namespace's file is set correctly.
    ns.__file__ = name

    # Inherit the eval namespace of the evaluating Module/Target/Dependency.
    parent_vars = context.get_exec_vars(get_call_context())
    scope = ChainDict(vars(ns), parent_vars)

    context.load_script(name, scope)
    return ns
  else:
    scope = context.get_exec_vars(context.load_module(name))
    return ObjectFromMapping(scope, name)


def option_default(name, value):
  return context.options.setdefault(name, value)


def get_output_directory(target, *subdir):
  return path.join(context.build_directory, target.module.name, target.name, *subdir)


if sys.platform.startswith('win32'):
  OS = OsInfo('windows', 'win32', os.name, 'x86_64' if os.environ.get('ProgramFiles(x86)') else 'x86')
elif sys.platform.startswith('darwin'):
  OS = OsInfo('macos', 'darwin', 'posix', 'x86_64' if sys.maxsize > 2**32 else 'x86')
elif sys.platform.startswith('linux'):
  OS = OsInfo('linux', 'linux', 'posix', 'x86_64' if sys.maxsize > 2**32 else 'x86')
else:
  raise EnvironmentError('(yet) unsupported platform: {}'.format(sys.platform))


BUILD = BuildInfo(context.build_variant)


__all__ = ['fmt', 'glob']

import sys
from . import core, path


def get_call_context(stackdepth=1, dependency=True, target=True, module=True):
  """
  Returns the #core.Module, #core.Target or #core.Dependency from the
  parent stackframe. Raises a #RuntimeError if it can not be determined.
  """

  scope = sys._getframe(stackdepth+1).f_globals
  if dependency and isinstance(scope.get('dependency'), core.Dependency):
    return scope['dependency']
  elif target and isinstance(scope.get('target'), core.Target):
    return scope['target']
  elif module and isinstance(scope.get('module'), core.Module):
    return scope['module']
  raise RuntimeError('Call context could not be determined')


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
    parent = obj.directory()
  return path.glob(patterns, parent, excludes)

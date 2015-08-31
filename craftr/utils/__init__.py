# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

from . import lists
from . import path
from . import proxy


class DataEntity(object):
  ''' Container for data of a module or a script. '''

  def __init__(self, entity_id):
    super().__init__()
    self.__entity_id__ = entity_id
    self.__entity_deps__ = []

  def __repr__(self):
    return '<DataEntity {0!r}>'.format(self.__entity_id__)

  def __getattr__(self, name):
    for dep in reversed(self.__entity_deps__):
      try:
        return getattr(dep, name)
      except AttributeError:
        pass
    raise AttributeError(name)


def singleton(x):
  ''' Decorator for a singleton class or function. The class or
  function will be called and the result returned. '''

  return x()

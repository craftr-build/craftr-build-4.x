# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

__all__ = ('lmap', 'lzip',)


def lmap(func, iterable):
  ''' List-returning version of the `map()` built-in. '''

  return list(map(func, iterable))


def lzip(*args):
  ''' List-returning version of `zip()` built-in. '''

  return list(zip(*args))

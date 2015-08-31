# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

__all__ = ('lmap', 'lzip',)


def lmap(func, iterable):
  ''' List-returning version of the `map()` built-in. '''

  return list(map(func, iterable))


def lzip(*args):
  ''' List-returning version of `zip()` built-in. '''

  return list(zip(*args))


def autoexpand(lst):
  ''' Accepts a string, list of strings or a list of lists of strings
  or even deeper nested levels and expands it to a list of only strings.
  This is used to flatten concatenated command argument and file lists.
  Also accepts tuples. '''

  result = []
  stack = [lst]
  while stack:
    item = stack.pop()
    if isinstance(item, str):
      result.insert(0, item)
    elif isinstance(item, (list, tuple)):
      stack.extend(item)
    else:
      raise TypeError('autoexpand() only works with str and list', type(item))

  return result

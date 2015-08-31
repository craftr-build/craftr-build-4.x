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

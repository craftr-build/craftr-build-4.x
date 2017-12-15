"""
Iterator and stream processing utilities.
"""

import builtins
import functools
import itertools


class stream:
  """
  A wrapper for iterables that provides the stream processor functions of
  this module in an object-oriented interface.
  """

  def __init__(self, iterable):
    self.iterable = iter(iterable)

  def __iter__(self):
    return iter(self.iterable)

  def __getitem__(self, val):
    if isinstance(val, slice):
      return self.slice(val.start, val.stop, val.step)
    else:
      raise TypeError('{}() is only subscriptable with slices')

  @classmethod
  def register_method(cls, func, name=None):
    name = name or func.__name__
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
      return self.apply(func, *args, **kwargs)
    setattr(cls, name, wrapper)
    return func

  @classmethod
  def register_inverse_method(cls, func, name=None):
    name = name or func.__name__
    @functools.wraps(func)
    def wrapper(self, arg1, *args, **kwargs):
      return self.new(func(arg1, self.iterable, *args, **kwargs))
    setattr(cls, name, wrapper)
    return func

  def apply(self, func, *args, **kwargs):
    return self.new(func(self.iterable, *args, **kwargs))

  def new(self, iterable):
    return type(self)(iterable)


stream.register_method(itertools.islice, 'slice')
stream.register_method(itertools.groupby)
stream.register_method(itertools.cycle)
stream.register_method(itertools.combinations)
stream.register_method(itertools.permutations)
stream.register_inverse_method(itertools.dropwhile)
stream.register_inverse_method(itertools.takewhile)


@stream.register_method
def call(iterable, *a, **kw):
  """
  Calls every item in *iterable* with the specified arguments.
  """

  return (x(*a, **kw) for x in iterable)


@stream.register_method
def map(iterable, func, *a, **kw):
  """
  Iterable-first replacement of Python's built-in `map()` function.
  """

  return (func(x, *a, **kw) for x in iterable)


@stream.register_method
def filter(iterable, cond, *a, **kw):
  """
  Iterable-first replacement of Python's built-in `filter()` function.
  """

  return (x for x in iterable if cond(x, *a, **kw))


@stream.register_method
def unique(iterable, key=None):
  """
  Yields unique items from *iterable* whilst preserving the original order.
  """

  if key is None:
    key = lambda x: x

  seen = set()
  seen_add = seen.add
  for item in iterable:
    key_val = key(item)
    if key_val not in seen:
      seen_add(key_val)
      yield item


@stream.register_method
def chunks(iterable, n, fill=None):
  """
  Collects elements in fixed-length chunks.
  """

  return itertools.zip_longest(*[iter(iterable)] * n, fillvalue=fill)


@stream.register_method
def concat(iterables):
  """
  Similar to #itertools.chain.from_iterable().
  """

  for it in iterables:
    for element in it:
      yield element


@stream.register_method
def attr(iterable, attr_name):
  """
  Applies #getattr() on all elements of *iterable*.
  """

  return (getattr(x, attr_name) for x in iterable)


@stream.register_method
def item(iterable, key):
  """
  Applies `__getitem__` on all elements of *iterable*.
  """

  return (x[key] for x in iterable)


@stream.register_method
def of_type(iterable, types):
  """
  Filters using #isinstance().
  """

  return (x for x in iterable if isinstance(x, types))


@stream.register_method
def partition(iterable, pred):
  """
  Use a predicate to partition items into false and true entries.
  """

  t1, t2 = itertools.tee(iterable)
  return itertools.filterfalse(pred, t1), builtins.filter(pred, t2)

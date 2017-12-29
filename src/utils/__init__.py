
import functools
import itertools


def getter(name, key=None):
  """
  Creates a getter-only property for the specified *name*.
  """

  if not key:
    key = lambda x: x

  def wrapper(self):
    return key(getattr(self, name))
  wrapper.__name__ = wrapper.__qualname__ = name
  return property(wrapper)


class stream:
  """
  A wrapper for iterables that provides the stream processor functions of
  this module in an object-oriented interface.
  """

  class dualmethod:
    def __init__(self, func):
      self.func = func
      functools.update_wrapper(self, func)
    def __get__(self, instance, owner):
      assert owner is not None
      if instance is not None:
        return functools.partial(self.func, owner, instance)
      return functools.partial(self.func, owner)

  def __init__(self, iterable):
    self.iterable = iter(iterable)

  def __iter__(self):
    return iter(self.iterable)

  def __getitem__(self, val):
    if isinstance(val, slice):
      return self.slice(val.start, val.stop, val.step)
    else:
      raise TypeError('{}() is only subscriptable with slices')

  @dualmethod
  def call(cls, iterable, *a, **kw):
    """
    Calls every item in *iterable* with the specified arguments.
    """

    return cls(x(*a, **kw) for x in iterable)

  @dualmethod
  def map(cls, iterable, func, *a, **kw):
    """
    Iterable-first replacement of Python's built-in `map()` function.
    """

    return cls(func(x, *a, **kw) for x in iterable)

  @dualmethod
  def filter(cls, iterable, cond, *a, **kw):
    """
    Iterable-first replacement of Python's built-in `filter()` function.
    """

    return cls(x for x in iterable if cond(x, *a, **kw))

  @dualmethod
  def unique(cls, iterable, key=None):
    """
    Yields unique items from *iterable* whilst preserving the original order.
    """

    if key is None:
      key = lambda x: x
    def generator():
      seen = set()
      seen_add = seen.add
      for item in iterable:
        key_val = key(item)
        if key_val not in seen:
          seen_add(key_val)
          yield item
    return cls(generator())

  @dualmethod
  def chunks(cls, iterable, n, fill=None):
    """
    Collects elements in fixed-length chunks.
    """

    return cls(itertools.zip_longest(*[iter(iterable)] * n, fillvalue=fill))

  @dualmethod
  def concat(cls, *iterables):
    """
    Similar to #itertools.chain.from_iterable().
    """

    def generator():
      for it in iterables:
        for element in it:
          yield element
    return cls(generator())

  @dualmethod
  def attr(cls, iterable, attr_name):
    """
    Applies #getattr() on all elements of *iterable*.
    """

    return cls(getattr(x, attr_name) for x in iterable)

  @dualmethod
  def item(cls, iterable, key):
    """
    Applies `__getitem__` on all elements of *iterable*.
    """

    return cls(x[key] for x in iterable)

  @dualmethod
  def of_type(cls, iterable, types):
    """
    Filters using #isinstance().
    """

    return cls(x for x in iterable if isinstance(x, types))

  @dualmethod
  def partition(cls, iterable, pred):
    """
    Use a predicate to partition items into false and true entries.
    """

    t1, t2 = itertools.tee(iterable)
    return cls(itertools.filterfalse(pred, t1), filter(pred, t2))

  @dualmethod
  def dropwhile(cls, iterable, pred):
    return cls(itertools.dropwhile(pred, iterable))

  @dualmethod
  def takewhile(cls, iterable, pred):
    return cls(itertools.takewhile(pred, iterable))

  @dualmethod
  def groupby(cls, iterable, key=None):
    return cls(itertools.groupby(iterable, key))

  @dualmethod
  def slice(cls, iterable, *args, **kwargs):
    return cls(itertools.islice(iterable, *args, **kwargs))

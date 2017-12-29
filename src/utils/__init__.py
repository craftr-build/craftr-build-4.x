
import collections
import functools
import itertools
import sys


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


class _named_meta(type):
  """
  Metaclass for the #named class.
  """

  def __init__(self, name, bases, data):
    # Inherit the annotations of the base classes, in the correct order.
    annotations = getattr(self, '__annotations__', {})
    if isinstance(annotations, (list, tuple)):
      for i, item in enumerate(annotations):
        if len(item) == 3:
          setattr(self, item[0], item[2])
          item = item[:2]
          annotations[i] = item
      annotations = collections.OrderedDict(annotations)
    new_annotations = collections.OrderedDict()
    for base in bases:
      base_annotations = getattr(base, '__annotations__', {})
      if isinstance(base_annotations, (list, tuple)):
        base_annotations = collections.OrderedDict(base_annotations)
      for key, value in base_annotations.items():
        if key not in annotations:
          new_annotations[key] = value
    new_annotations.update(annotations)
    self.__annotations__ = new_annotations
    super().__init__(name, bases, data)


class named(metaclass=_named_meta):
  """
  A base-class similar to #typing.NamedTuple, but mutable. Fields can be
  specified using Python 3.6 class-member annotations or by setting the
  `__annotations__` field to a list where each item is a member declaration
  that consists of two or three items where 1) is the name, 2) is the
  annotated value (type) and 3) is the default value for the field.
  """

  def __init__(self, *args, **kwargs):
    annotations = getattr(self, '__annotations__', {})
    if len(args) > len(annotations):
      raise TypeError('{}() expected {} positional arguments, got {}'
        .format(type(self).__name__, len(annotations), len(args)))
    if isinstance(annotations, (list, tuple)):
      annotations = collections.OrderedDict(annoations)

    for arg, (key, ant) in zip(args, annotations.items()):
      setattr(self, key, arg)
      if key in kwargs:
        raise TypeError('{}() duplicate value for argument "{}"'
          .format(type(self).__name__, key))

    for key, ant in annotations.items():
      if key in kwargs:
        setattr(self, key, kwargs.pop(key))
      elif not hasattr(self, key):
        raise TypeError('{}() missing argument "{}"'
          .format(type(self).__name__, key))

    for key in kwargs.keys():
      raise TypeError('{}() unexpected keyword argument "{}"'
        .format(type(self).__name__, key))

  def __repr__(self):
    members = ', '.join('{}={!r}'.format(k, getattr(self, k)) for k in self.__annotations__)
    return '{}({})'.format(type(self).__name__, members)

  def __iter__(self):
    for key in self.__annotations__:
      yield getattr(self, key)

  def asdict(self):
    return {k: getattr(self, k) for k in self.__annotations__}

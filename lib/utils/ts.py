"""
Thread-safety done right.

The `ts` module provides utilities for implementing thread-safe classes in
an easy and Pythonic pattern. Simply inherit from the `ts.object` class and
decorate critical methods with `@ts.method` or `@ts.property`.

In order to enter synchronized state for an object, it is generally
recommended to use the `ts.condition()` method in a Python `with` statement.
However, sometimes you want to synchronize the execution of a whole function
in which case you can use the `ts.method` and `ts.property` decorators.

# Example

```python
import ts from 'craftr/core/utils/ts'

class Box(ts.object):

  def __init__(self, value):
    self.value = value

  @ts.method
  def __repr__(self):
    return '<Box {!r}>'.format(self._value)

box = Box(None)
# Start some thread that modifies the value of 'box'
with ts.condition(box):
  ts.wait_for(box, lambda: box.value is not None)
  print('Got value:', box.value)
```
"""

import builtins
import contextlib
import functools
import time
import threading


class object(builtins.object):
  """
  The base for thread-safe classes. The class supports two optional keyword
  arguments. The two should be compatible with each other. Keep in mind that
  using a non-recursive lock strongly limits the compatibility of your class
  with existing algorithms and can easily lead to dead-locks.

  * `lock_class`: The class that is used for locking (#threading.RLock)
  * `condition_class`: The condition variable class (#threading.Condition)
    This condition class should support the context-manager interface for
    acquiring and releasing the inner lock-object.
  """

  def __init_subclass__(cls, lock_class=threading.RLock,
                             condition_class=threading.Condition,
                             **kwargs):
    cls._ts__lock_class = lock_class
    cls._ts__condition_class = condition_class
    super().__init_subclass__(**kwargs)

  def __new__(cls, *args, **kwargs):
    self = super().__new__(cls)
    self._ts__lock = cls._ts__lock_class()
    self._ts__cond = cls._ts__condition_class(self._ts__lock)
    return self


def lock(obj):
  """
  Returns the lock object of an instance of the #ts.object class.
  """

  return obj._ts__lock


def condition(obj):
  """
  Returns the condition object of an instance of the #ts.object class. Use
  this function
  """

  return obj._ts__cond


def wait(obj, timeout=None):
  """
  Calls the `wait(timeout)` method on *obj*'s condition object. This will
  block the current thread until #notify() or #notify_all() was called on
  the object.

  Note that this method can only be used inside a #condition() context.

  This function always returns #True.
  """

  condition(obj).wait(timeout)
  return True


def wait_for(obj, check, timeout=None, time=time):
  """
  Waits for *obj* until the specified *check* is #True. The check must be
  invoked using #notify() or #notify_all(). *check* can be a function that
  takes 0 or 1 positional arguments. If it accepts a single argument, that
  argument is *obj*.

  If the *timeout* is exceeded, #False is returned, otherwise #False.

  Note that this method can only be used inside a #condition() context.
  """

  if check.__code__.co_argcount != 0:
    check = functools.partial(check, obj)

  if timeout is None:
    while not check():
      wait(obj)
    return True

  timeout = float(timeout)
  t_start = time.clock()
  while not check():
    t_delta = time.clock() - t_start
    if t_delta >= timeout:
      return False
    wait(obj, timeout - t_delta)

  return True


def notify(obj):
  """
  Notify a thread waiting for the object about a change and allow it to
  continue. Note that this method can only be used inside a #condition()
  context.
  """

  condition(obj).notify()


def notify_all(obj):
  """
  Notify all threads waiting for the object about a change and allow them to
  continue. Note that this method can only be used inside a #condition()
  context.
  """

  condition(obj).notify_all()


def method(func):
  """
  A decorator for instance methods that enters the #condition() context before
  invoking the wrapped function *func*.
  """

  @functools.wraps(func)
  def wrapper(self, *args, **kwargs):
    with condition(self):
      return func(self, *args, **kwargs)
  return wrapper


class property(builtins.property):
  """
  A thread-safe version of the Python #property decorator.
  """

  def __get__(self, obj, type=None):
    with condition(obj):
      return super().__get__(obj, type)

  def __set__(self, obj, value):
    with condition(obj):
      super().__set__(obj, value)

  def __delete__(self, obj):
    with condition(obj):
      super().__delete__(obj)

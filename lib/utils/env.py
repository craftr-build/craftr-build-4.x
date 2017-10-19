"""
Utilities for working with the system environment. Most notably, modifications
to #os.environ should only be performed while acquiring the #lock in
multithreaded applications.
"""

import contextlib
import os
import threading

#: An r-lock that should be used when doing modifications to #os.environ.
lock = threading.RLock()


@contextlib.contextmanager
def override(environ, merge=True):
  """
  Temporarily overrides #os.environ with the *environ* dictionary. If *merge*
  is #True, the *environ* will be updated on top of #os.environ. This method
  is thread-safe as long as #lock is used to synchronise access to #os.environ.
  """

  if not isinstance(environ, dict):
    raise TypeError('environ must be dict')

  if not merge and not environ:
    # Nothing changes.
    yield
    return

  old_env = os.environ.copy()
  if not merge:
    os.environ.clear()
  os.environ.update(environ)

  try:
    yield
  finally:
    os.environ.clear()
    os.environ.update(old_env)

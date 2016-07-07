# Copyright (C) 2016  Niklas Rosenstein
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
'''
Tools for working with environment variables.
'''

from craftr import path, environ
from contextlib import contextmanager


def append_path(pth):
  '''
  Appends *pth* to the ``PATH`` environment variable.
  '''

  environ['PATH'] = environ['PATH'] + path.pathsep + pth


def prepend_path(pth):
  '''
  Prepends *pth* to the ``PATH`` environment variable.
  '''

  environ['PATH'] = pth + path.pathsep + environ['PATH']


@contextmanager
def override_environ(new_environ=None):
  '''
  Context-manager that restores the old :data:`environ` on exit.

  :param new_environ: A dictionary that will update the :data:`environ`
    inside the context-manager.
  '''

  old_environ = environ.copy()
  try:
    if new_environ:
      environ.update(new_environ)
    yield
  finally:
    environ.clear()
    environ.update(old_environ)


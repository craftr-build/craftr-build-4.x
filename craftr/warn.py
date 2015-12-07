# Copyright (C) 2015  Niklas Rosenstein
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

from .magic import get_frame
import warnings


def warn(message, prefix=None, stacklevel=1, warntype=RuntimeWarning):
  if not prefix:
    prefix = ''
    frame = get_frame(stacklevel)
    if '_warn_prefix' in frame.f_locals:
      prefix = frame.f_locals['_warn_prefix']
  if prefix:
    prefix = '{0}: '.format(prefix)
  warnings.warn('{0}{1}'.format(prefix, message), warntype, stacklevel + 1)


def invalid_option(name, value, prefix=None, detail=None, stacklevel=1, warntype=RuntimeWarning):
  message = 'invalid option: {0}={1!r}'.format(name, value)
  if detail:
    message += ' ({0})'.format(detail)
  warn(message, prefix, stacklevel + 1, warntype)


def unused_kwargs(kwargs, prefix=None, stacklevel=1, warntype=RuntimeWarning):
  if not kwargs:
    return
  message = 'unused keyword arguments ' + ','.join(map(str, kwargs.keys()))
  warn(message, prefix, stacklevel + 1, warntype)

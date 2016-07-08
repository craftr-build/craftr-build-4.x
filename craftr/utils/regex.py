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
Regex utility functions.

.. autofunction:: search_get_groups
'''

import re


def search_get_groups(pattern, subject, mode=0):
  '''
  Performs :func:`re.search` and returns a list of the captured groups,
  *including* the complete matched string as the first group. If the
  regex search was unsuccessful, a list with that many items containing
  None is returned.
  '''

  pattern = re.compile(pattern, mode)
  ngroups = pattern.groups + 1

  res = pattern.search(subject)
  if not res:
    return [None] * ngroups
  else:
    groups = list(res.groups())
    groups.insert(0, res.group(0))
    return groups

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

from craftr import environ, path

import os
import sys


def append_path(pth):
  ''' Append *pth* to the `PATH` environment variable. '''

  environ['PATH'] = environ['PATH'] + path.pathsep + pth


def prepend_path(pth):
  ''' Prepend *pth* to the `PATH` environment variable. '''

  environ['PATH'] = pth + path.pathsep + environ['PATH']


def find_program(name):
  ''' Finds the program *name* in the `PATH` and returns the full
  absolute path to it. On Windows, this also takes the `PATHEXT`
  variable into account.

  Arguments:
    name: The name of the program to find.
  Returns:
    str: The absolute path to the program.
  Raises:
    FileNotFoundError: If the program could not be found in the PATH. '''

  if path.isabs(name):
    return name

  iswin = sys.platform.startswith('win32')
  iscygwin = sys.platform.startswith('cygwin')
  if iswin and '/' in name or '\\' in name:
    return path.abspath(name)
  elif iswin and path.sep in name:
    return path.abspath(name)

  if iswin:
    pathext = environ['PATHEXT'].split(path.pathsep)
  elif iscygwin:
    pathext = [None, '.exe']
  else:
    pathext = [None]

  for dirname in environ['PATH'].split(path.pathsep):
    fullname = path.join(dirname, name)
    for ext in pathext:
      extname = (fullname + ext) if ext else fullname
      if path.isfile(extname) and os.access(extname, os.X_OK):
        return extname
  raise FileNotFoundError(name)

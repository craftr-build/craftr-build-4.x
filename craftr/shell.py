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
This module is similar to the `subprocess.run()` interface that is
available since Python 3.5 but is a bit customized so that it works
better with Craftr.
'''

__all__ = ['safe', 'quote', 'format', 'split', 'join', 'find_program',
           'test_program', 'CalledProcessError', 'TimeoutExpired',
           'CompletedProcess', 'run', 'pipe', 'PIPE', 'STDOUT']

from . import path, environ
from subprocess import PIPE, STDOUT

import os
import re
import shlex
import subprocess
import sys


class safe(str):
  ''' If this object is passed to `quote()`, it will not be escaped. '''
  pass


def split(s):
  # xxx: do we need to set posix=False on Windows?
  return shlex.split(s)


def quote(s):
  ''' Enhanced implementation for Windows systems as the original
  `shlex.quote()` function uses single-quotes on Windows which can lead
  to problems. '''

  if isinstance(s, safe):
    return s
  if os.name == 'nt' and os.sep == '\\':
    s = s.replace('"', '\\"')
    if re.search('\s', s):
      s = '"' + s + '"'
    return s
  else:
    return shlex.quote(s)


def format(fmt, *args, **kwargs):
  ''' Similar to :meth:`str.format`, but this function will escape all
  arguments with the :func:`quote` function. '''

  return fmt.format(*map(quote, args), **{k: quote(v) for k, v in kwargs.items()})


def join(cmd):
  ''' Join a list of strings to a single command. '''

  return ' '.join(map(quote, cmd))


def find_program(name):
  """
  Finds the program *name* in the `PATH` and returns the full
  absolute path to it. On Windows, this also takes the `PATHEXT`
  variable into account.

  :param name: The name of the program to find.
  :return: :class:`str` -- The absolute path to the program.
  :raise FileNotFoundError: If the program could not be found in the PATH.
  :raise PermissionError: If a candidate for "name" was found but
    it is not executable.
  """

  if path.isabs(name):
    if not path.isfile(name):
      raise FileNotFoundError(name)
    if not os.access(name, os.X_OK):
      raise PermissionError('{0!r} is not executable'.format(name))
    return name

  iswin = sys.platform.startswith('win32')
  iscygwin = sys.platform.startswith('cygwin')
  if iswin and '/' in name or '\\' in name:
    name = path.abspath(name)
  elif iswin and path.sep in name:
    name = path.abspath(name)

  if iswin:
    pathext = environ['PATHEXT'].split(path.pathsep)
  elif iscygwin:
    pathext = [None, '.exe']
  else:
    pathext = [None]

  first_candidate = None
  for dirname in environ['PATH'].split(path.pathsep):
    fullname = path.join(dirname, name)
    for ext in pathext:
      extname = (fullname + ext) if ext else fullname
      if path.isfile(extname):
        if os.access(extname, os.X_OK):
          return extname
        if first_candidate is None:
          first_candidate = extname

  if first_candidate:
    raise PermissionError('{0!r} is not executable'.format(first_candidate))
  raise FileNotFoundError(name)


def test_program(name):
  """
  Uses :func:`find_program` to find the path to "name" and returns
  True if it could be found, False otherwise.
  """

  try:
    find_program(name)
  except OSError:
    return False
  return True


class _ProcessError(Exception):
  ''' Base class that implements the attributes and behaviour of errors
  that will inherit from this exception class. '''

  def __init__(self, process):
    self.process = process

  @property
  def returncode(self):
    return self.process.returncode

  @property
  def cmd(self):
    return self.process.cmd

  @property
  def stdout(self):
    return self.process.stdout

  @property
  def stderr(self):
    return self.process.stderr

  @property
  def output(self):
    return self.process.output


class CalledProcessError(_ProcessError):
  ''' This exception is raised when a process exits with a non-zero
  returncode and the run was to be checked for such state. The exception
  contains the process information. '''

  def __str__(self):
    return '{0!r} exited with non-zero exit-code {1}'.format(self.cmd, self.returncode)


class TimeoutExpired(_ProcessError):
  ''' This exception is raised when a process did not exit after a
  specific timeout. If this exception was raised, the child process
  has already been killed. '''

  def __init__(self, process, timeout):
    super().__init__(process)
    assert isinstance(timeout, (int, float))
    self.timeout = timeout

  def __str__(self):
    return '{0!r} expired timeout of {1} second(s)'.format(self.cmd, self.timeout)


class CompletedProcess(object):
  ''' This class represents a completed process. '''

  __slots__ = 'cmd returncode stdout stderr'.split()

  def __init__(self, cmd, returncode, stdout, stderr):
    self.cmd = cmd
    self.returncode = returncode
    self.stdout = stdout
    self.stderr = stderr

  def __repr__(self):
    return '<CompletedProcess {0!r} with exit-code {1}>'.format(self.cmd, self.returncode)

  @property
  def output(self):
    return self.stdout

  @output.setter
  def output(self, value):
    self.stdout = value

  def decode(self, encoding):
    if encoding is None:
      return
    if self.stdout is not None:
      self.stdout = self.stdout.decode(encoding)
    if self.stderr is not None:
      self.stderr = self.stderr.decode(encoding)

  def check_returncode(self):
    if self.returncode != 0:
      raise CalledProcessError(self)


def run(cmd, *, stdin=None, input=None, stdout=None, stderr=None, shell=False,
    timeout=None, check=False, cwd=None, encoding=sys.getdefaultencoding()):
  '''
  Run the process with the specified *cmd*. If *cmd* is a list of
  commands and *shell* is True, the list will be automatically converted
  to a properly escaped string for the shell to execute.

  .. note::

    If "shell" is True, this function will manually check if the file
    exists and is executable first and raise :class:`FileNotFoundError`
    if not.

  :raise CalledProcessError: If *check* is True and the process exited with
    a non-zero exit-code.
  :raise TimeoutExpired: If *timeout* was specified and the process did not
    finish before the timeout expires.
  :raise OSError: For some OS-level error, eg. if the program could not be
      found.
  '''

  if shell and not isinstance(cmd, str):
    cmd = join(cmd)
  elif not shell and isinstance(cmd, str):
    cmd = split(cmd)

  if shell:
    # Wrapping the call in a shell invokation will not raise an
    # exception when the file could not actually be executed, thus
    # we have to check it manually.
    if isinstance(cmd, str):
      program = split(cmd)[0]
    else:
      program = cmd[0]
    find_program(program)

  try:
    popen = subprocess.Popen(
      cmd, stdin=stdin, stdout=stdout, stderr=stderr, shell=shell, cwd=cwd)
    stdout, stderr = popen.communicate(input, timeout)
  except subprocess.TimeoutExpired as exc:
    # TimeoutExpired.stderr available only since Python3.5
    stderr = getattr(exc, 'stderr', None)
    process = CompletedProcess(exc.cmd, None, exc.output, stderr)
    process.decode(encoding)
    raise TimeoutExpired(process, timeout)
  except OSError as exc:
    if not exc.filename and os.name == 'nt':
      # Windows does not include the name of the file with which
      # the error occured in the exception message.
      if isinstance(cmd, str):
        program = split(cmd)[0]
      else:
        program = cmd[0]
      exc.filename = program
    raise

  process = CompletedProcess(cmd, popen.returncode, stdout, stderr)
  process.decode(encoding)
  if check:
    process.check_returncode()
  return process


def pipe(*args, merge=True, **kwargs):
  ''' Like `run()`, but pipes stdout and stderr to a buffer instead of
  directing them to the current standard out and error files. If *merge*
  is True, stderr will be merged into stdout. '''

  kwargs.setdefault('stdout', PIPE)
  kwargs.setdefault('stderr', STDOUT if merge else PIPE)
  return run(*args, **kwargs)

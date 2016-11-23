# The Craftr build system
# Copyright (C) 2016  Niklas Rosenstein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import shlex
import subprocess
import sys

from . import path
from subprocess import PIPE, STDOUT

class safe(str):
  """
  If this object is passed to `quote()`, it will not be escaped.
  """

  pass


def split(s):
  """
  Enhanced implementation of :func:`shlex.split`.
  """

  result = shlex.split(s, posix=(os.name != 'nt'))
  if os.name == 'nt':
    # With posix=False, shlex.split() will not interpret \ as the
    # escape character (which is what we need on windows), but it
    # will also not eliminate quotes, which is what we need to do
    # here now.
    quotes = '\"\''
    result = [x[1:-1] if (x and x[0] in quotes and x[-1] in quotes) else x for x in result]
  return result


def quote(s, for_ninja=False):
  """
  Enhanced implementation of :func:`shlex.quote` as it generates single-quotes
  on Windows which can lead to problems.
  """

  if isinstance(s, safe):
    return s
  if os.name == 'nt' and os.sep == '\\':
    s = s.replace('"', '\\"')
    if re.search('\s', s):
      s = '"' + s + '"'
  else:
    s = shlex.quote(s)
  if for_ninja:
    # Fix escaped $ variables on Unix, see issue craftr-build/craftr#30
    s = re.sub(r"'(\$\w+)'", r'\1', s)
  return s


def format(fmt, *args, **kwargs):
  """"
  Similar to :meth:`str.format`, but this function will escape all arguments
  with the :func:`quote` function. This is useful to easily generate commands.

  .. code:: python

    >>> format('gcc {} -o {}', 'my source/main.c', 'spaces are bad/main')
    'gcc "my source/main.c" -o "spaces are bad/main"'
  """

  return fmt.format(*map(quote, args), **{k: quote(v) for k, v in kwargs.items()})


def join(cmd, for_ninja=False):
  """
  Join a list of strings to a single command string.
  """

  return ' '.join(quote(x, for_ninja=for_ninja) for x in cmd)


def find_program(name):
  """
  Finds the program *name* in the directories listed by the ``PATH``
  environment variable and returns the full absolute path to it. On Windows,
  this also takes the `PATHEXT` variable into account.

  :param name: The name of the program to find.
  :return: :class:`str` -- The absolute path to the program.
  :raise FileNotFoundError: If the program could not be found in the PATH.
  :raise PermissionError: If a candidate for "name" was found but
    it is not executable.
  """

  if path.dirname(name):
    name = path.abs(name)
  if path.isabs(name):
    if not path.isfile(name):
      raise FileNotFoundError(name)
    if not os.access(name, os.X_OK):
      raise PermissionError('{0!r} is not executable'.format(name))
    return name

  iswin = sys.platform.startswith('win32')
  iscygwin = sys.platform.startswith('cygwin')
  if iswin and '/' in name or '\\' in name:
    name = path.abs(name)
  elif iswin and path.sep in name:
    name = path.abs(name)

  if iswin:
    pathext = os.environ['PATHEXT'].split(path.pathsep)
  elif iscygwin:
    pathext = [None, '.exe']
  else:
    pathext = [None]

  first_candidate = None
  for dirname in os.environ['PATH'].split(path.pathsep):
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
  Uses :func:`find_program` to find the path to *name* and returns
  True if it could be found, False otherwise.
  """

  try:
    find_program(name)
  except OSError:
    return False
  return True


class _ProcessError(Exception):
  """
  Base class that implements the attributes and behaviour of errors
  that will inherit from this exception class.
  """

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
  """
  This exception is raised when a process exits with a non-zero
  returncode and the run was to be checked for such state. The exception
  contains the process information.
  """

  def __str__(self):
    return '{0!r} exited with non-zero exit-code {1}'.format(self.cmd, self.returncode)


class TimeoutExpired(_ProcessError):
  """
  This exception is raised when a process did not exit after a
  specific timeout. If this exception was raised, the child process
  has already been killed.
  """

  def __init__(self, process, timeout):
    super().__init__(process)
    assert isinstance(timeout, (int, float))
    self.timeout = timeout

  def __str__(self):
    return '{0!r} expired timeout of {1} second(s)'.format(self.cmd, self.timeout)


class CompletedProcess(object):
  """
  This class represents a completed process.
  """

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
  """
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
  """

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
  """
  Like `run()`, but pipes stdout and stderr to a buffer instead of
  directing them to the current standard out and error files. If *merge*
  is True, stderr will be merged into stdout.
  """

  kwargs.setdefault('stdout', PIPE)
  kwargs.setdefault('stderr', STDOUT if merge else PIPE)
  return run(*args, **kwargs)

# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import os
import re
import shlex
import subprocess
import sys


class Process(object):
  ''' A simple wrapper for `subprocess.Popen` class with easier access
  to the processes standard and error output. When an instance of this
  class is created, the process will immediately be started and waited
  for termination.

  Arguments:
    command: The argument list for the process.
    shell (bool): True if the command should be executed in the shell.
    merge (bool): True if the standard output should be merged with
      the error output, False if not.
  '''

  class ExitCodeError(Exception):
    ''' Raised if the process exits with a non-zero exit-code. '''

    def __init__(self, process):
      self.process = process

    def __str__(self):
      return "Process '{0}' exited with exit-code {1}".format(
        self.process.command[0], self.process.returncode)

  def __init__(self, command, shell=False, merge=False,
      input_=None, encoding=sys.getdefaultencoding()):
    super().__init__()
    stderr = subprocess.STDOUT if merge else subprocess.PIPE
    self.p = subprocess.Popen(command, shell=shell,
      stdout=subprocess.PIPE, stderr=stderr)
    self.stdout, self.stderr = self.p.communicate(input_)
    if encoding is not None:
      self.stdout = self.stdout.decode(encoding)
      if not merge:
        self.stderr = self.stderr.decode(encoding)
    if self.returncode != 0:
      raise Process.ExitCodeError(self)

  @property
  def returncode(self):
    return self.p.returncode


def quote(s):
  ''' Enhanced implementation for Windows systems as the original
  `shlex.quote()` function uses single-quotes on Windows which can lead
  to problems. '''

  if os.name == 'nt' and os.sep == '\\':
    s = s.replace('"', '\\"')
    if re.search('\s', s):
      s = '"' + s + '"'
    return s
  else:
    return shlex.quote(s)

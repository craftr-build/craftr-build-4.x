# -*- mode: python -*-
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
A very small interface for querying information about a Git repository.

Examples
~~~~~~~~

Display a note in console if build is started with unversioned changes
in the Git repository.

.. code:: python

  git = load_module('git').Git(project_dir)
  info('Current Version:', git.describe())
  if git.status(exclude='??'):
    info('Unversioned changes present.')

Export a ``GIT_VERSION.h`` header file into the build directory (not
to mess with your source tree!)

.. code:: python

  from craftr import *
  from craftr.ext import git

  def write_gitversion():
    filename = path.buildlocal('include/GIT_VERSION.h')
    dirname = path.dirname(filename)
    if session.export:
      path.makedirs(dirname)
      description = git.Git(project_dir).describe()
      with open(filename, 'w') as fp:
        fp.write('#pragma once\\n#define GIT_VERSION "{}"\\n'.format(description))
    return dirname

  gitversion_dir = write_gitversion()  # Add this to your includes
'''

__all__ = ['Git']

from craftr import shell


class Git(object):

  def __init__(self, git_dir):
    super().__init__()
    self.git_dir = git_dir

  def _popen(self, *args, **kwargs):
    return shell.pipe(*args, check=True, merge=False, cwd=self.git_dir, **kwargs)

  def status(self, include=None, exclude=None):
    result = []
    output = self._popen(['git', 'status', '--porcelain']).stdout
    for line in output.split('\n'):
      status, filename = line[:2].strip(), line[3:]
      if not status or not filename:
        continue
      if include is not None and status not in include:
        continue
      if exclude is not None and status in exclude:
        continue
      result.append((status, filename))
    return result

  def describe(self, mode='tags', all=False, fallback=True):
    if mode not in ('tags', 'contains'):
      raise ValueError('invalid describe mode {!r}'.format(mode))
    command = ['git', 'describe', '--{}'.format(mode)]
    if all:
      command.append('--all')
    try:
      return self._popen(command).stdout.strip()
    except shell.CalledProcessError as exc:
      if fallback and 'No names found' in exc.stderr:
        # Let's create an alternative description instead.
        sha = self._popen(['git', 'rev-parse', 'HEAD']).output[:7]
        count = int(self._popen(['git', 'rev-list', 'HEAD', '--count']).output.strip())
        return '{}-{}'.format(count, sha)
      raise


  def branches(self):
    command = ['git', 'branch']
    for line in self._popen(command).stdout.split('\n'):
      parts = line.split()
      if len(parts) == 2:
        yield parts
      else:
        yield ['', parts[0]]

  def branch(self):
    command = ['git', 'symbolic-ref', '--short', 'HEAD']
    try:
      return self._popen(command).stdout.strip()
    except Process.ExitCodeError as exc:
      raise ValueError(exc.process.stderr.strip())

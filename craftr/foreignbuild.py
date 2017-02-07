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

from craftr.core.session import session
from craftr.core.logging import logger
from craftr.utils import path, shell
from craftr.defaults import gentarget, gtn

import hashlib
import os
import stat


def configure(filename='configure', args=(), cwd=None, env=None, show_output=False):
  """
  Run a GNU autotools `configure` script. If *cwd* is not specified, the
  current working directory will be the parent directory of *filename*.
  This function will skip invokation of the configure script if arguments
  and environment haven't change since the last time.
  """

  args = list(args)
  if cwd and not path.isabs(filename):
    filename = path.join(cwd, filename)
  filename = path.abs(filename)
  if env is None: env = {}

  # Hash the arguments and environment to find out of it changed.
  md5 = hashlib.md5()
  [md5.update(x.encode()) for x in args]
  [(md5.update(k.encode()), md5.update(v.encode())) for k, v in sorted(env.items())]
  [md5.update(str(int(path.getmtime(filename))).encode())]
  md5 = md5.hexdigest()

  # Check if the hash matches the hash from the previous invokation.
  hashes = session.cache.setdefault('foreignbuild', {}).setdefault('configure_hashes', {})
  if md5 == hashes.get(filename):
    logger.info("skipping configure:", filename)
    return
  logger.info("running configure:", filename)

  # Execute the file.
  if cwd is None: cwd, filename = path.split(filename)
  invoke = shell.pipe if show_output else shell.run
  invoke([filename] + args, cwd=cwd, env=env, check=True, shell=True)


  hashes[filename] = md5


def make(filename='Makefile', *args, cwd=None, inputs=(), outputs=(), name=None):
  """
  Create a target that executes the specified Makefile. If *cwd* is not
  specified, it defaults to the parent directory if *filename*.
  """

  if cwd and not path.isabs(filename):
    filename = path.join(cwd, filename)
  filename = path.abs(filename)

  # TODO
  if cwd is None: cwd, filename = path.split(filename)

  inputs = list(inputs)
  inputs.append(filename)

  filename = path.rel(filename, cwd, nopar=True)
  command = ['make', '-f', filename] + list(args)
  return gentarget([command], inputs, outputs, cwd=cwd, name=gtn(name, 'make'))

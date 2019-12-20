# -*- coding: utf8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2018  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This is the Python program that is invoked to run a build. It communicates
with the Action server created by Ninja to retrieve the build commands,
avoiding the need to read the whole build graph for every build that
Ninja runs.
"""

import argparse
import contextlib
import io
import json
import nr.fs as path
import os
import re
import socket
import shlex
import struct
import subprocess
import sys

from nr.stream import Stream as stream
from craftr.core import build
from craftr.utils.sh import quote

verbose = os.environ.get('CRAFTR_VERBOSE') == 'true'


def recvall(sock, size):
  buffer = io.BytesIO()
  bytes_read = 0
  while bytes_read < size:
    data = sock.recv(size - bytes_read)
    if not data:
      break
    buffer.write(data)
    bytes_read += len(data)
  return buffer.getvalue()


class BuildClient:
  """
  Communicates with the build server to read build information.
  """

  def __init__(self, server_address=None):
    if server_address is None:
      server_address = os.environ.get('CRAFTR_BUILD_SERVER')
      if not server_address or server_address.count(':') != 1:
        raise ValueError('CRAFTR_BUILD_SERVER not set or invalid')
    if isinstance(server_address, str):
      server_address = server_address.split(':', 1)
      server_address[1] = int(server_address[1])
    self._client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._client.connect(tuple(server_address))

  def __enter__(self):
    return self

  def __exit__(self, *args):
    self.end_connection()

  def _send_receive(self, request):
    request = json.dumps(request).encode('utf8')
    self._client.sendall(struct.pack('!I', len(request)))
    self._client.sendall(request)
    response_size = struct.unpack('!I', self._client.recv(4))[0]
    response_data = recvall(self._client, response_size).decode('utf8')
    response = json.loads(response_data)
    if 'error' in response:
      raise RuntimeError(response['error'])
    return response

  def reload_build_server(self):
    self._send_receive({'reload_build_server': True})

  def get_build_set(self, master: build.Master, target: str, operator: str, build_set: int):
    response = self._send_receive({
      'target': target,
      'operator': operator,
      'build_set': build_set
    })
    target = build.Target.from_json(master, response['data']['target'])
    bset = next(iter(target.operators)).build_sets[0]
    return bset, response['data']['hash'], response['data']['additional_args']

  def end_connection(self):
    self._client.close()


def error(*args, **kwargs):
  kwargs['file'] = sys.stderr
  print(*args, **kwargs)


def main(argv=None, prog=None):
  parser = argparse.ArgumentParser(prog=prog)
  parser.add_argument('target')
  parser.add_argument('operator')
  parser.add_argument('build_set', type=int)
  parser.add_argument('hash')
  args = parser.parse_args()

  master = build.Master()
  with BuildClient() as client:
    bset, bset_hash, additional_args = client.get_build_set(
      master, args.target, args.operator, args.build_set)
    if bset_hash != args.hash:
      error('fatal: build set hash inconsistency ({!r} != {!r})'.format(
        bset_hash, args.hash))
      return 1

  operator = bset.operator

  # Ensure that the output directories exist.
  created_dirs = set()
  for f in stream.concat(bset.outputs.values()):
    d = path.dir(f)
    if d not in created_dirs:
      path.makedirs(d)

  # Update the environment and working directory.
  os.environ.update(bset.get_environ())
  cwd = bset.get_cwd()
  if cwd:
    os.chdir(cwd)

  # Generate the command list.
  commands = bset.get_commands()

  # Used to print the command-list on failure.
  def print_command_list(current=-1):
    if cwd:
      error('Working directory:', os.getcwd())
    error('Command list:')
    for i, cmd in enumerate(commands):
      error('>' if current == i else ' ', '$', ' '.join(map(quote , cmd)))

  if verbose:
    print_command_list()

  # Execute the subcommands.
  with contextlib.ExitStack() as stack:
    for i, (cmd, cmd_template) in enumerate(zip(commands, bset.operator.commands)):
      cmd = stack.enter_context(cmd_template.with_response_file(cmd))

      # Add the additional_args to the last command in the chain.
      if i == len(commands) - 1:
        cmd = cmd + additional_args
      try:
        code = subprocess.call(cmd)
      except OSError as e:
        error(e)
        code = 127
      if code != 0:
        error('\n' + '-'*60)
        error('fatal: "{}" exited with code {}.'.format(operator.id, code))
        print_command_list(i)
        error('-'*60 + '\n')
        return code

  # Check if all output files have been produced by the commands.
  outputs = list(stream.concat(bset.outputs.values()))
  missing_files = [x for x in outputs if not path.exists(x)]
  if missing_files:
    error('\n' + '-'*60)
    error('fatal: "{}" produced only {} of {} listed output files.'
      .format(operator.id, len(outputs) - len(missing_files),
        len(outputs)))
    error('The missing files are:')
    for x in missing_files:
      error('  -', x)
    print_command_list()
    error('-'*60 + '\n')
    return 1

  """
  # TODO: Optional output files ..? Currently not supported in the BuildSet
  # Show a warning about missing optional output files.
  outputs = list(build.files.tagged('out,optional'))
  missing_files = [x for x in outputs if not path.exists(x)]
  if missing_files:
    error('\n' + '-'*60)
    error('warning: missing optional output files')
    for x in missing_files:
      error('  -', x)
    error('-'*60)
  """

  return 0


if __name__ == '__main__':
  sys.exit(main())

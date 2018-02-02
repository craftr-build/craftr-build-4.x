# This is the Python program that is invoked to run a build. It communicates
# with the Action server created by Ninja to retrieve the build commands,
# avoiding the need to read the whole build graph for every build that
# Ninja runs.

import argparse
import io
import json
import os
import re
import socket
import shlex
import struct
import subprocess
import sys
from itertools import chain
from craftr import path
from craftr.common import BuildSet

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


class RemoteBuildGraph:
  """
  Communicates with the Craftr action server to retrieve the build
  information. It does not yield #BuildAction instances but instead
  JSON objects.
  """

  def __init__(self, server_address=None):
    if server_address is None:
      server_address = os.environ.get('CRAFTR_ACTION_SERVER')
      if not server_address or server_address.count(':') != 1:
        raise ValueError('CRAFTR_ACTION_SERVER not set or invalid')
    if isinstance(server_address, str):
      server_address = server_address.split(':', 1)
      server_address[1] = int(server_address[1])
    self._client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._client.connect(tuple(server_address))
    self._actions = {}

  def __getitem__(self, key):
    try:
      action = self._actions[key]
    except KeyError:
      action = self._request(key)
    if action is None:
      raise KeyError(key)
    return action

  def _request(self, key):
    if not isinstance(key, str): return None
    request = json.dumps({'action': key}).encode('utf8')
    self._client.sendall(struct.pack('!I', len(request)))
    self._client.sendall(request)
    response_size = struct.unpack('!I', self._client.recv(4))[0]
    response_data = recvall(self._client, response_size).decode('utf8')
    response = json.loads(response_data)
    if response.get('error') == 'DoesNotExist':
      return None
    elif 'error' in response:
      raise RuntimeError(response['error'])
    return response['data']

  def hash(self, action):
    """
    Generate a hash for an action in the #BuildGraph.
    """

    return action['hash']

  def end_connection(self):
    self._client.close()


def error(*args, **kwargs):
  kwargs['file'] = sys.stderr
  print(*args, **kwargs)


def run_build_action(graph, node_name, index, main_build_cell=None):
  if '^' in node_name:
    node_name, node_hash = node_name.split('^', 1)
  else:
    node_hash = None
  if node_name.startswith(':'):
    if not main_build_cell:
      error('relative action name not supported, no main build cell')
      return 1
    node_name = '//' + main_build_cell + node_name

  try:
    node = graph[node_name]
  except KeyError:
    error('fatal: build node "{}" does not exist'.format(node_name))
    return 1
  if not isinstance(node, dict):
    node = node.as_json()  # In case we have a standard BuildGraph.

  if node_hash is not None and node_hash != graph.hash(node):
    error('fatal: build node hash inconsistency, maybe try --prepare-build')
    return 1

  build = BuildSet.from_json(node['builds'][index])

  # TODO: The additional args feature should be explicitly supported by the
  #       build node, allowing it to specify a position where the additional
  #       args will be rendered.
  #       Usually, the option only makes sense for targets that run a single
  #       command such as cxx.run(), java.run(), etc.
  additional_args = node.get('additional_args', []) #get_additional_args_for(node_name)

  # Ensure that the output directories exist.
  created_dirs = set()
  for filename in build.files.tagged('out'):
    directory = path.dir(filename)
    if directory not in created_dirs and directory:
      os.makedirs(directory, exist_ok=True)
      created_dirs.add(directory)

  # Update the environment and working directory.
  old_env = os.environ.copy()
  os.environ.update(node['environ'] or {})
  if node['cwd']:
    os.chdir(node['cwd'])

  # Generate the command list.
  commands = [build.subst(x) for x in node['commands']]

  # Used to print the command-list on failure.
  def print_command_list(current=-1):
    if node['cwd']:
      error('Working directory:', os.getcwd())
    error('Command list:'.format(node_name))
    for i, cmd in enumerate(commands):
      error('>' if current == i else ' ', '$', ' '.join(map(shlex.quote , cmd)))

  if verbose:
    print_command_list()

  # Execute the subcommands.
  for i, cmd in enumerate(commands):
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
      error('fatal: "{}" exited with code {}.'.format(node_name, code))
      print_command_list(i)
      error('-'*60 + '\n')
      return code

  # Check if all output files have been produced by the commands.
  outputs = list(build.files.tagged('out', '!optional'))
  missing_files = [x for x in outputs if not os.path.exists(x)]
  if missing_files:
    error('\n' + '-'*60)
    error('fatal: "{}" produced only {} of {} listed output files.'
      .format(node_name, len(outputs) - len(missing_files),
        len(outputs)))
    error('The missing files are:')
    for x in missing_files:
      error('  -', x)
    print_command_list()
    error('-'*60 + '\n')
    return 1

  # Show a warning about missing optional output files.
  outputs = list(build.files.tagged('out', 'optional'))
  missing_files = [x for x in outputs if not os.path.exists(x)]
  if missing_files:
    error('\n' + '-'*60)
    error('warning: missing optional output files')
    for x in missing_files:
      error('  -', x)
    error('-'*60)

  return 0


def main(argv=None):
  parser = argparse.ArgumentParser(prog='craftr-ninja-buildslave')
  parser.add_argument('action')
  parser.add_argument('index', type=int)
  args = parser.parse_args()
  graph = RemoteBuildGraph()
  return run_build_action(graph, args.action, args.index)


if __name__ == '__main__':
  sys.exit(main())

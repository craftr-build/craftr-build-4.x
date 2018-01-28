"""
Craftr uses an "Action Server" that serves the action information from the
master process to the Craftr slave process (invoked via the build backend).
This is to avoid that the slave process has to parse the build graph file
every time.

    [ Craftr Master Process ]   <- communicates with -\
    \-> [ Build Backend (eg. Ninja) ]                 |
        \-> [ Craftr Slave Process (invokes the actual build commands) ]
"""

import concurrent.futures
import json
import socket
import socketserver
import struct
import threading
import {BuildAction, BaseBuildGraph} from './buildgraph'


class ActionRequestHandler(socketserver.BaseRequestHandler):

  build_graph = None

  def handle(self):
    try:
      while True:
        data = self.request.recv(4)
        if len(data) == 0: break
        request_size = struct.unpack('!I', data)[0]
        request_data = json.loads(self.request.recv(request_size).decode('utf8'))
        action_key = request_data.get('action')
        try:
          action = self.build_graph[action_key]
        except KeyError:
          response_data = {'error': 'DoesNotExist', 'action': action_key}
        else:
          response_data = {'action': action_key, 'data': action.as_json()}
        response_data = json.dumps(response_data).encode('utf8')
        self.request.sendall(struct.pack('!I', len(response_data)))
        self.request.sendall(response_data)
      self.request.close()
    except ConnectionResetError:
      pass

class ActionServer:

  def __init__(self, build_graph):
    assert isinstance(build_graph, BaseBuildGraph)
    self._build_graph = build_graph
    self._server = socketserver.ThreadingTCPServer(('localhost', 0), self._request_handler)
    self._server.timeout = 0.5
    self._thread = None
    self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)

  def __enter__(self):
    self._pool.__enter__()
    self.serve()
    return self

  def __exit__(self, *args):
    self._pool.__exit__(*args)
    self.shutdown()

  def _request_handler(self, *args, **kwargs):
    handler = object.__new__(ActionRequestHandler)
    handler.build_graph = self._build_graph
    handler.__init__(*args, **kwargs)
    #self._pool.submit(handler.__init__, *args, **kwargs)

  def address(self):
    return self._server.server_address

  def serve(self):
    if self._thread and self._thread.is_alive():
      raise RuntimeError('ActionServer already/still running.')
    self._thread = threading.Thread(target=self._server.serve_forever)
    self._thread.start()

  def shutdown(self, wait=True):
    self._server.shutdown()
    if wait and self._thread:
      self._thread.join()


class RemoteBuildGraph(BaseBuildGraph):
  """
  Represents a remote build graph server by an #ActionServer.
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
    response = json.loads(self._client.recv(response_size).decode('utf8'))
    if response.get('error') == 'DoesNotExist':
      return None
    elif 'error' in response:
      raise RuntimeError(response['error'])
    return BuildAction.from_json(response['data'])

  def end_connection(self):
    self._client.close()

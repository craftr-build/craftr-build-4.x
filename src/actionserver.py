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
  additional_args = None

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
          response_data['data']['hash'] = self.build_graph.hash(response_data['data'])
          response_data['data']['additional_args'] = self._get_additional_args(action_key)
        response_data = json.dumps(response_data).encode('utf8')
        self.request.sendall(struct.pack('!I', len(response_data)))
        self.request.sendall(response_data)
      self.request.close()
    except ConnectionResetError:
      pass

  def _get_additional_args(self, action):
    if action not in self.additional_args:
      action = action.partition('#')[0]
      if action not in self.additional_args:
        return []
    return shlex.split(self.additional_args[action])


class ActionServer:

  def __init__(self, build_graph, additional_args=None):
    assert isinstance(build_graph, BaseBuildGraph)
    self._build_graph = build_graph
    self._additional_args = additional_args or {}
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
    handler.additional_args = self._additional_args
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

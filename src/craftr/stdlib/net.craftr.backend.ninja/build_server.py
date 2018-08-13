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
Craftr uses a "Build Server" that serves the action information from the
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


class JsonifyProxy:

  def __init__(self, obj, **kwargs):
    self._obj = obj
    self._kwargs = kwargs

  def to_json(self, *args, **kwargs):
    kwargs.update(self._kwargs)
    return self._obj.to_json(*args, **kwargs)


class RequestHandler(socketserver.BaseRequestHandler):

  master = None
  additional_args = None

  def handle(self):
    try:
      while True:
        data = self.request.recv(4)
        if len(data) == 0: break
        request_size = struct.unpack('!I', data)[0]
        request = json.loads(self.request.recv(request_size).decode('utf8'))

        if not all(x in request for x in ('target', 'operator', 'build_set')):
          response = {'error': 'BadRequest'}
        else:
          try:
            target = self.master.targets[request['target']]
            operator = target.operators[request['operator']]
            bset = operator.build_sets[request['build_set']]
          except KeyError:
            response = {'error': 'DoesNotExist'}
          else:
            proxy = JsonifyProxy(operator, build_sets=[bset])
            proxy = JsonifyProxy(target, operators=[proxy])
            data = {
              'target': proxy.to_json(),
              'hash': bset.compute_hash(),
              'additional_args': self._get_additional_args(target, operator, bset)
            }
            response = {'data': data}

        response = json.dumps(response).encode('utf8')
        self.request.sendall(struct.pack('!I', len(response)))
        self.request.sendall(response)

      self.request.close()
    except ConnectionResetError:
      pass

  def _get_additional_args(self, target: 'Target', operator: 'Operator', bset: 'BuildSet'):
    # TODO
    #if action not in self.additional_args:
    #  action = action.partition('#')[0]
    #  if action not in self.additional_args:
    #    return []
    #return shlex.split(self.additional_args[action])
    return []


class BuildServer:

  def __init__(self, master, additional_args=None):
    self._master = master
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
    handler = object.__new__(RequestHandler)
    handler.master = self._master
    handler.additional_args = self._additional_args
    handler.__init__(*args, **kwargs)
    #self._pool.submit(handler.__init__, *args, **kwargs)

  def address(self):
    return self._server.server_address

  def serve(self):
    if self._thread and self._thread.is_alive():
      raise RuntimeError('BuildServer already/still running.')
    self._thread = threading.Thread(target=self._server.serve_forever)
    self._thread.start()

  def shutdown(self, wait=True):
    self._server.shutdown()
    if wait and self._thread:
      self._thread.join()

# -*- coding: utf8; -*-
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
''' This module implements the Craftr runtime server that enables to call
Python functions from the servers process. If this file is executed as a
script, it provides a client to call a function on the server. The server
location is read from the `CRAFTR_RTS` environment variable. '''

from craftr import environ, shell, magic, info, warn, error
from collections import deque
from functools import partial

import argparse
import codecs
import contextlib
import craftr
import io
import os
import urllib.parse
import time
import threading
import traceback
import signal
import socket
import sys

try:
  from multiprocessing import cpu_count
except ImportError:
  cpu_count = lambda: 1


_modname = ':rts-client:' if __name__ == '__main__' else ':rts:'
info = partial(info, module_name=_modname)
warn = partial(warn, module_name=_modname)
error = partial(error, module_name=_modname, raise_=False)

# The maximum number of bytes per message data.
MAX_BYTES = 999

# Sent when an invalid message was sent to the server. The connection
# is immediately closed afterwards. The message data eventually is an
# error message encoded as UTF8.
MSG_INVALID_REQUEST = b'ireq'

# Sent as response to message that don't require an explicit answer.
MSG_NOOP = b'noop'

# Message for exchaning key-value pairs. The message data is a
# string that contains <key>=<value>. The default encoding is UTF8.
# The encoding can be changed by sending the header charset=<coding>.
MSG_HEADER = b'head'

# Sent to start the command on the server side.
MSG_RUN = b'run!'

# Kill the process started with MSG_RUN.
MSG_KILL = b'kill'

# Message to request a package from the server.
MSG_PACKAGE_REQUEST = b'preq'

# This message is sent as a reply to MSG_PACKAGE_REQUEST when there is
# new output available from the executed command.
MSG_PACKAGE_OUTPUT = b'pout'

# This message is sent a as a reply to MSG_PACKAGE_REQUEST when the
# command has finished executing and the exit-code is available. The
# message data is the commands exit-code as ascii number.
MSG_PACKAGE_RESULT = b'pres'


def send_message(sock, message_type, message_data=b''):
  if not isinstance(message_type, bytes):
    raise TypeError('message_type must be bytes')
  if len(message_type) != 4:
    raise ValueError('message_type must be exactly 4 chars')
  if not isinstance(message_data, bytes):
    raise TypeError('message_data must be bytes')
  if len(message_data) > MAX_BYTES:
    raise ValueError('message_data must be smaller than {0} bytes'.format(MAX_BYTES))
  message_header = message_type + ('%04d' % len(message_data)).encode('ascii')
  sock.send(message_header)
  sock.send(message_data)


def parse_message(sock):
  message_header = sock.recv(8)
  if not message_header:
    return (None, None)
  if len(message_header) != 8:
    raise ValueError('invalid message_header: {0!r}'.format(message_header))
  message_type = message_header[:4]
  try:
    message_length = int(message_header[4:])
    if message_length < 0:
      raise ValueError
  except ValueError:
    emsg = 'invalid message_length: {0!r}'.format(message_length)
    raise ValueError(emsg) from None
  message_data = sock.recv(message_length)
  return (message_type, message_data)


def parse_uri(uri):
  ''' Parses an URI of the format `host:port` and returns a tuple of
  the two, or raises a `ValueError` if the uri is invalid. '''

  res = urllib.parse.urlparse('xxx://' + uri)  # We need a scheme for parsing.
  if (res.scheme != 'xxx' or res.path or res.params or res.query or res.fragment
      or res.username or res.password or not res.hostname or not res.port):
    raise ValueError('expected host:port format, got {0!r}'.format(uri))
  return (res.hostname, res.port)


class InvalidRequest(Exception):
  def __init__(self, message_type, message):
    self.message_type = message_type
    self.message = message
  def __str__(self):
    return '{0}: {1}'.format(self.message_type.decode('unicode_escape'), self.message)


class InvalidResponse(Exception):
  pass


class ThreadIO(object):
  ''' Redirects IO based on the current thread ID. '''

  def __init__(self, default_fp):
    self._default_fp = default_fp
    self._local = threading.local()

  @property
  def dest_file(self):
    return getattr(self._local, 'fp', None) or self._default_fp

  @dest_file.setter
  def dest_file(self, fp):
    self._local.fp = fp

  def __getattr__(self, name):
    return getattr(self.dest_file, name)


class RWFile(object):
  ''' Wraps a random access stream and supports two distinct file
  offset pointers for reading and writing. '''

  @contextlib.contextmanager
  def _fakelock():
    yield

  def __init__(self, buffer, synchronized=True, lock=None):
    self._buffer = buffer
    self._rpos = self._wpos = buffer.tell()
    self._lock = lock or (threading.Lock() if synchronized else RWFile._fakelock())

  @property
  def closed(self):
    return self._buffer.closed

  def seekable(self):
    return False

  def readable(self):
    return True

  def writable(self):
    return True

  def read(self, n):
    with self._lock:
      self._buffer.seek(self._rpos)
      data = self._buffer.read(n)
      self._rpos += len(data)
    return data

  def readline(self, size=None):
    with self._lock:
      self._buffer.seek(self._rpos)
      line = self._buffer.readline(size)
      self._rpos += len(line)
    return line

  def write(self, data):
    with self._lock:
      self._buffer.seek(self._wpos)
      count = self._buffer.write(data)
      self._wpos += count
    return count

  def writelines(self, lines):
    for line in lines:
      self.write(line)


class _RequestHandler(object):
  ''' Represents a client request handler. '''

  def __init__(self, server, sock, addr, close_socket=True):
    super().__init__()
    self.server = server
    self.session = server.session
    self.sock = sock
    self.addr = addr
    self.headers = {'coding': 'utf8'}
    self.accept = True
    self.thread = None
    self.stdin = None
    self.stdout = None
    self.stderr = None
    self.result = None
    self.lock = threading.RLock()

    try:
      self.info('connection accepted')
      while self.accept:
        self.accept_message()
    except InvalidRequest as exc:
      send_text(self.sock, MSG_INVALID_REQUEST, str(exc).encode(self.coding))
    finally:
      if close_socket:
        self.sock.close()

  @property
  def coding(self):
    return self.headers['coding']

  def info(self, *args, **kwargs):
    if self.session.verbosity > 0:
      info('[{0}:{1}]'.format(*self.addr), *args, **kwargs)

  def accept_message(self):
    message_type, data = parse_message(self.sock)
    if message_type is None:
      self.accept = False
      return

    if message_type == MSG_HEADER:
      if self.thread:
        self.send_message(MSG_INVALID_REQUEST, 'already running')

      # Parse the header kay/value pair.
      data = data.decode(self.coding)
      key, sep, value = data.partition('=')
      if not sep or not value:
        self.send_text(MSG_INVALID_REQUEST, 'invalid header format')
        return False
      key = key.lower().strip()
      if key == 'coding':
        # Make sure that this would actually be a valid encoding.
        try:
          codecs.lookup(value)
        except codecs.LookupError:
          self.send_text(MSG_INVALID_REQUEST, 'invalid coding: {0!r}'.format(value))
          return False
      self.headers[key] = value
      self.send_message(MSG_NOOP)
      return

    elif message_type == MSG_RUN:
      if self.thread:
        self.send_text(MSG_INVALID_REQUEST, 'already started')
        return

      command = self.headers.get('command')
      if not command:
        self.send_text(MSG_INVALID_REQUEST, 'command header not sent')
        return

      try:
        target = self.session.targets[command]
      except KeyError:
        self.send_text(MSG_INVALID_REQUEST, '{0!r} is not a registered target'.format(command))
        return
      if not target.rts_func:
        self.send_text(MSG_INVALID_REQUEST, '{0!r} is not an RTS target'.format(command))
        return

      # xxx does it make sense to use the _RequestHandler.lock
      # to synchronize read/write from/to the streams?
      self.stdin = RWFile(io.BytesIO(), lock=self.lock)
      self.stdout = RWFile(io.BytesIO(), lock=self.lock)
      self.stderr = self.stdout  # xxx: separate stderr?

      def wrapper():
        def reset():
          thread_stdin.dest_file = None
          thread_stdout.dest_file = None
          thread_stderr.dest_file = None

        # xxx: any check that the ThreadIO objects are still attached?
        try:
          thread_stdin.dest_file = io.TextIOWrapper(io.BufferedReader(self.stdin))
          thread_stdout.dest_file = io.TextIOWrapper(io.BufferedWriter(self.stdout))
          thread_stderr.dest_file = thread_stdout.dest_file  # io.TextIOWrapper(io.BufferedWriter(self.stderr))
          try:
            result = target.execute_task()
          except craftr.TaskError as exc:
            error(str(exc))
            result = exc.result
          if result is None:
            result = 0
          elif not isinstance(result, int):
            print(result)
            result = 1
          with self.lock:
            self.result = result
        except BaseException as exc:
          with self.lock:
            self.result = 1
          try:
            traceback.print_exc()
          finally:
            # xxx: debug: Enable if output of the exception message in
            # Craftr server process is desired.
            pass
            # reset()
            #traceback.print_exc()

      def context_enterer():
        with magic.enter_context(craftr.session, self.session, secret=True):
          return wrapper()

      self.info('@@ {0}()'.format(command))
      with self.lock:
        self.result = None
        self.thread = threading.Thread(target=context_enterer)
        self.thread.start()
      self.send_message(MSG_NOOP)
      return

    elif message_type == MSG_KILL:
      if not self.thread:
        self.send_text(MSG_INVALID_REQUEST, 'not started')
        return
      command = self.headers['command']
      self.info('killing {0}() [note: the function still runs in the background]'.format(command))
      self.thread = None
      with self.lock:
        # xxx: we should tell the thread executing wrapper() that the
        # result of the function should not be saved.
        self.result = None
      self.send_message(MSG_NOOP)
      return

    elif message_type == MSG_PACKAGE_REQUEST:
      if not self.thread:
        self.send_text(MSG_INVALID_REQUEST, 'not started')
        return
      data = self.stdout.readline(MAX_BYTES)
      if data:
        self.send_message(MSG_PACKAGE_OUTPUT, data)
      elif not self.thread.is_alive():
        # We don't need to synchronize the access since it can't be
        # modified when the thread is finished.
        assert isinstance(self.result, int)
        self.send_text(MSG_PACKAGE_RESULT, str(self.result))
      else:
        self.send_message(MSG_NOOP)
      return

    else:
      warn('unknown message: {0!r}'.format(message_type))
      self.send_text(MSG_INVALID_REQUEST, 'unknown message type: {0!r}'.format(message_type))
      return

  def send_message(self, message_type, data=b''):
    return send_message(self.sock, message_type, data)

  def send_text(self, message_type, text):
    data = text.encode(self.coding)
    if len(data) > MAX_BYTES:
      raise InvalidRequest('text for {0!r} too big'.format(message_type))
    return send_message(self.sock, message_type, data)


class _Client(object):
  ''' Client implementation for communicating with the Craftr runtime server. '''

  def __init__(self, host, port, timeout=1.0):
    super().__init__()
    self.sock = socket.socket()
    self.sock.connect((host, port))
    self.sock.settimeout(timeout)

  def _send(self, message_type, data=b'', expect=None):
    send_message(self.sock, message_type, data)
    result = parse_message(self.sock)
    if result[0] == MSG_INVALID_REQUEST:
      raise InvalidRequest(message_type, result[1].decode('utf8'))
    if expect and result[0] != expect:
      emsg = 'expected {0!r} from server, received {1!r}'.format(expect, result[0])
      raise InvalidResponse(emsg)
    return result

  def send_command(self, command):
    self._send(MSG_HEADER, b'command=' + command.encode('utf8'), expect=MSG_NOOP)

  def send_run(self):
    self._send(MSG_RUN, expect=MSG_NOOP)

  def send_kill(self):
    self._send(MSG_KILL, expect=MSG_NOOP)

  def recv_package(self):
    message_type, data = self._send(MSG_PACKAGE_REQUEST)
    if message_type == MSG_PACKAGE_RESULT:
      # Command has completed, contains the result.
      try:
        exit_code = int(data.decode('utf8'))
      except ValueError:
        emsg = 'MSG_PACKAGE_RESULT data could not be converted to int'
        raise InvalidResponse(emsg) from None
      return message_type, exit_code
    elif message_type in (MSG_PACKAGE_OUTPUT, MSG_NOOP):
      return message_type, data
    elif message_type is None:
      # Communication ceased.
      raise InvalidResponse('expected package response, but communication ceased')
    else:
      raise InvalidResponse('unexpected response: {0!r}'.format(message_type))


class CraftrRuntimeServer(object):
  ''' This class implements the Craftr socket communication. It uses
  a very simple protocol: At the begin of each data chunk comes a
  message identifier of 4 chars. After the three chars follows a
  whitespace and an ascii number of exactly 4 digits that represents
  the content length of the message. It is always the client that
  initiates communication. The server responds with another message.

  Note: The message size is effectively limited to 9999 (`MAX_BYTES`)
  bytes. '''

  def __init__(self, session, max_threads=None):
    super().__init__()
    self.session = session
    self.host = None
    self.port = None
    self.sock = None
    self.threads = deque()
    self.max_threads = max_threads or cpu_count()
    self.state = 'off'
    self.lock_state = threading.Lock()
    self.lock_sock = threading.Lock()

  def bind(self, host='localhost', port=0, timeout=0.5):
    self.sock = socket.socket()
    self.sock.bind((host, port))
    self.sock.settimeout(timeout)
    self.host, self.port = self.sock.getsockname()

  def close(self):
    with self.lock_state:
      if self.state != 'off':
        raise RuntimeError('server is still running, can not close socket')
    if not self.sock:
      raise RuntimeError('server is not bound')
    with self.lock_sock:
      self.sock.close()
      self.sock = self.host = self.port = None

  def stop(self):
    ''' Wait for all connections to close and stop the server. '''

    with self.lock_state:
      self.state = 'stopping'
    while True:
      with self.lock_state:
        if not self.threads:
          break
        thread = self.threads.popleft()
      thread.join()
    with self.lock_state:
      self.state = 'off'

  def serve_forever(self, listen=5):
    ''' Accept client connections until `stop()` is called. '''

    if not self.sock:
      raise RuntimeError('server is not bound')
    with self.lock_state:
      if self.state == 'running':
        raise RuntimeError('server already running')
      self.state = 'running'

    self.sock.listen(listen)
    while True:
      with self.lock_state:
        # Filter out threads that have completed.
        self.threads = deque(t for t in self.threads if t.is_alive())
        if self.state != 'running':
          break
      with self.lock_sock:
        try:
          sock, addr = self.sock.accept()
        except socket.timeout:
          continue
      thread = threading.Thread(target=_RequestHandler, args=[self, sock, addr])
      thread.start()
      with self.lock_state:
        self.threads.append(thread)

  def serve_forever_async(self, *args, **kwargs):
    thread = threading.Thread(target=self.serve_forever, args=args, kwargs=kwargs)
    thread.start()
    return thread

  @property
  def running(self):
    ''' True if the server is currently running and bound to an
    address, False if not. '''

    return bool(self.sock)


def client_main():
  parser = argparse.ArgumentParser()
  parser.add_argument('command', help='the command to invoke, usually the name of a Python function')
  args = parser.parse_args()

  try:
    uri = parse_uri(environ.get('CRAFTR_RTS', ''))
  except ValueError:
    parser.error('invalid CRAFTR_RTS = {0!r}'.format(environ.get('CRAFTR_RTS', '')))

  client = _Client(uri[0], uri[1])
  client.send_command(args.command)
  client.send_run()

  try:
    while True:
      pkg_type, pkg_data = client.recv_package()
      if pkg_type == MSG_PACKAGE_RESULT:
        assert isinstance(pkg_data, int)
        return pkg_data
      elif pkg_type == MSG_PACKAGE_OUTPUT:
        # Write the command's binary output to the standard output.
        assert isinstance(pkg_data, bytes)
        os.write(1, pkg_data)
      elif pkg_type == MSG_NOOP:
        time.sleep(0.1)  # Sleep shortly, maybe then data will become available.
      else:
        assert False, "unexpected package type: {0!r}".format(pkg_type)
  except BaseException as exc:
    try:
      client.send_kill()
    finally:
      if not isinstance(exc, KeyboardInterrupt):
        raise

  return 0


# xxx: Is there any other way than hard-patching the sys module?
thread_stdin = sys.stdin = ThreadIO(sys.stdin)
thread_stdout = sys.stdout = ThreadIO(sys.stdout)
thread_stderr = sys.stderr = ThreadIO(sys.stderr)


if __name__ == '__main__':
  sys.exit(client_main())

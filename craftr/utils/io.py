# The MIT License (MIT)
#
# Copyright (c) 2018 Niklas Rosenstein
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

import hashlib
import os


def file_hash(filename, algorithm='sha1'):
  h = hashlib.new(algorithm)
  with open(filename, 'rb', buffering=0) as f:
    for b in iter(lambda : f.read(128*1024), b''):
      h.update(b)
  return h.hexdigest()


class AutoRestoreMtimeFile:
  """
  Open a file on the filesystem. When the file is closed and the hash of the
  file has not changed, its original modification timestamp is restored.
  """

  def __init__(self, name, *args, **kwargs):
    try:
      self.hash = file_hash(name)
      self.time = os.path.getmtime(name)
    except FileNotFoundError:
      self.hash = None
      self.time = None
    self.name = name
    self._fp = open(name, *args, **kwargs)

  def __enter__(self):
    return self

  def __exit__(self, *args):
    self.close()

  def close(self):
    self._fp.close()
    if self.hash is not None and self.hash == file_hash(self.name):
      os.utime(self.name, (os.path.getatime(self.name), self.time))

  def write(self, data):
    return self._fp.write(data)

  def tell(self):
    return self._fp.tell()

  def fileno(self):
    return self._fp.fileno()

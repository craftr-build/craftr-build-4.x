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

__all__ = ['get_proto_meta', 'ProtoCompiler']

from craftr import Target
import re


def get_proto_meta(filename):
  ''' Extracts the package declaration and various meta information
  from the specified .proto file. '''

  messages = []
  meta = {}
  with open(filename, 'r') as fp:
    for line in fp:
      index = line.find('//')
      if index >= 0:
        line = line[:index]
      match = re.search('package\s+([\w\.]+)\s*;', line)
      if match:
        meta['package'] = match.group(1)
        continue
      match = re.search('option\s+([\w_]+)\s*=\s*(.*);', line)
      if match:
        meta[match.group(1)] = match.group(2).strip()
        continue
      match = re.search('message\s+(\w+)', line)
      if match:
        messages.append(match.group(1))
        continue
  return messages, meta


def camelify(name):
  parts = name.split('_')
  return ''.join(x.capitalize() for x in parts)


class ProtoCompiler(object):
  ''' Interface for the Google Protocol Buffers Compiler. '''

  def __init__(self, program='protoc'):
    super().__init__()
    self.program = program

  def compile(self, sources, proto_path=(), cpp_out=None, java_out=None, python_out=None):
    if not any([cpp_out, java_out, python_out]):
      raise ValueError('need at least cpp_out, java_out or python_out')
    if not proto_path:
      proto_path = [path.commonpath(sources)]
    command = [self.program]
    command += ['--proto_path={0}'.format(x) for x in proto_path]
    command += ['--cpp_out={0}'.format(cpp_out)] if cpp_out else []
    command += ['--java_out={0}'.format(java_out)] if java_out else []
    command += ['--python_out={0}'.format(python_out)] if python_out else []
    command += ['$in']

    outputs = []
    for fn in sources:
      if not fn.endswith('.proto'):
        raise ValueError('not a .proto file: {0!r}'.format(fn))

      messages, meta = get_proto_meta(fn)
      fn = fn[:-6]
      base = path.basename(fn)
      camel_base = camelify(base)
      camel_messages = [camelify(x) for x in messages]

      for dirname in proto_path:
        relp = path.relpath(fn, dirname)
        if relp == path.curdir or relp.startswith(path.pardir):
          continue
        relp = path.join(path.dirname(relp), path.basename(relp).lower())

        if cpp_out:
          outputs.append(path.join(cpp_out, relp + '.pb.cc'))

        if java_out:
          # Determine the Java package name.
          package = meta.get('java_package', '""').strip('"')
          if not package:
            package = meta.get('package', '')
          parentdir = package.replace('.', path.sep)

          # Determine the outer class name.
          outer_class = meta.get('java_outer_classname', '')
          if not outer_class:
            if camel_base in camel_messages:
              outer_class = camel_base + 'OuterClass'
            else:
              outer_class = camel_base

          outputs.append(path.join(java_out, parentdir, outer_class + '.java'))

        if python_out:
          outputs.append(path.join(python_out, relp + '_pb2.py'))

    return Target(command, sources, outputs)

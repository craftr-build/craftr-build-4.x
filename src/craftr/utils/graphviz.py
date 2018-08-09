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
This module provides an object oriented interface for building GraphViz
graphs.
"""

import io


def escape(value):
  value = str(value)
  value = value.replace('"', '\\"').replace('{', '\\{').replace('}', '\\}')
  value = value.replace('\n', '\\n')
  return value


def attr(key, value, semicolon=True):
  res = '{}="{}"'.format(key, escape(value))
  if semicolon:
    res += ';'
  return res


class Graph:

  def __init__(self, bidirectional=True):
    self.bidirectional = bidirectional
    self.settings = {}
    self.nodes = {}
    self.clusters = {}

  def setting(self, name, **attrs):
    self.settings[name] = attrs

  def cluster(self, id, cluster=None, **attrs):
    if id in self.clusters:
      raise ValueError('cluster {!r} already exists'.format(id))
    cluster = self.clusters[id] = Cluster(id, cluster, **attrs)
    cluster.graph = self
    return cluster

  def node(self, id, cluster=None, **attrs):
    if id in self.nodes:
      raise ValueError('node {!r} already exists'.format(id))
    node = self.nodes[id] = Node(id, cluster, **attrs)
    node.graph = self
    return node

  def edge(self, aid, bid):
    self.nodes[bid]
    self.nodes[aid].connections.add(bid)
    if self.bidirectional:
      self.nodes[bid].connections.add(bid)

  def render(self, writer=None):
    to_str = (writer is None)
    if to_str:
      writer = Writer(io.StringIO())
    elif not isinstance(writer, Writer):
      writer = Writer(writer)
    writer.line('graph {' if self.bidirectional else 'digraph {')
    writer.indent()
    for key, value in self.settings.items():
      writer.line('{} [{}];'.format(key, ' '.join(attr(k, v, False) for k, v in value.items())))
    for node in self.nodes.values():
      if not node.cluster:
        node.render(writer)
    for cluster in self.clusters.values():
      if not cluster.cluster:
        cluster.render(writer)
    writer.dedent()
    writer.line('}')
    if to_str:
      return writer._fp.getvalue()


class Node:

  def __init__(self, id, cluster=None, **attrs):
    self.id = id
    self.attrs = attrs
    self._cluster = None
    self.cluster = cluster
    self.graph = None
    self.connections = set()

  @property
  def cluster(self):
    return self._cluster

  @cluster.setter
  def cluster(self, cluster):
    if self._cluster:
      self._cluster.nodes.remove(self.id)
    self._cluster = cluster
    if cluster and type(self) is Node:
      cluster.nodes.add(self.id)
    elif cluster and type(self) is Cluster:
      cluster.subclusters.add(self.id)

  def render(self, writer):
    attrs = ' '.join(attr(k, v, False) for k, v in self.attrs.items())
    writer.line('"{}" [{}];'.format(self.id, attrs))
    for other_id in self.connections:
      writer.line('"{}" {} "{}"'.format(self.id, '-' if self.graph.bidirectional else '->', other_id))


class Cluster(Node):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.nodes = set()
    self.subclusters = set()

  def node(self, *args, **kwargs):
    return self.graph.node(*args, cluster=self, **kwargs)

  def subcluster(self, *args, **kwargs):
    return self.graph.cluster(*args, cluster=self, **kwargs)

  def render(self, writer):
    writer.line('subgraph "cluster_{}" {{'.format(self.id))
    writer.indent()
    for key, value in self.attrs.items():
      writer.line(attr(key, value))
    for node in [self.graph.nodes[x] for x in self.nodes]:
      node.render(writer)
    for cluster in [self.graph.clusters[x] for x in self.subclusters]:
      cluster.render(writer)
    writer.dedent()
    writer.line('}')


class Writer:

  def __init__(self, fp):
    self._indent = 0
    self._fp = fp

  def line(self, line):
    self._fp.write('  ' * self._indent + line + '\n')

  def indent(self):
    self._indent += 1

  def dedent(self):
    self._indent -= 1

"""
Access maven artifacts.
"""

from xml.etree import ElementTree
import xml.dom.minidom as minidom
import requests

import logging as log # TODO
#import log from 'craftr/utils/log'

def requests_get_check(*args, **kwargs):
  response = requests.get(*args, **kwargs)
  response.raise_for_status()
  return response


class Artifact:
  """
  Represents a Maven artifact. Maven artifacts consist of a group id, an
  artifact id and optionally a version. Additionally, the artifact may
  contain additional information when it was used with a #MavenRepository,
  eg. timestamp and build number.
  """

  @classmethod
  def from_id(cls, id_str):
    group, artifact, version = id_str.split(':')
    return cls(group, artifact, version)

  def __init__(self, group, artifact, version=None, scope='compile', optional=False):
    self.group = group
    self.artifact = artifact
    self.version = version
    self.timestamp = None
    self.build_number = None
    self.scope = scope
    self.optional = optional

  def __hash__(self):
    return hash(self.as_tuple())

  def __eq__(self, other):
    if isinstance(other, Artifact):
      return self.as_tuple() == other.as_tuple()
    return False

  def __str__(self):
    return '{}:{}:{}'.format(self.group, self.artifact, self.version)

  def __repr__(self):
    return 'Artifact("{}:{}:{}")'.format(self.group, self.artifact, self.version)

  def as_tuple(self):
    return (self.group, self.artifact, self.version)

  def is_snapshot(self):
    if self.version:
      return 'SNAPSHOT' in self.version
    return False

  def to_local_path(self, ext):
    return '{s.artifact}-{s.version}.{e}'.format(s=self, e=ext)

  def to_maven_name(self, ext):
      template = '{g}/{s.artifact}/{s.version}/{s.artifact}-{s.version}.{e}'
      return template.format(g=self.group.replace('.', '/'), s=self, e=ext)

  def to_maven_snapshot_name(self, ext):
      template = '{g}/{s.artifact}/{s.version}/'\
                 '{s.artifact}-{v}-{s.timestamp}-{s.build_number}.{e}'
      return template.format(g=self.group.replace('.', '/'), s=self, e=ext,
          v=self.version.replace('-SNAPSHOT', ''))

  def to_maven_metadata(self):
    return '{}/{}'.format(self.group.replace('.', '/'), self.artifact) + '/maven-metadata.xml'


class MavenRepository:

  def __init__(self, name, uri):
    self.name = name
    self.uri = uri.rstrip('/')
    self.pom_cache = {}
    self.pom_not_found = set()
    self.metadata_cache = {}

  def __repr__(self):
    return 'MavenRepository(name={!r}, uri={!r})'.format(self.name, self.uri)

  def download_jar(self, artifact, local_path):
    """
    Downloads a JAR file of the #Artifact *artifact* to *local_path*.
    """

    url = self.get_artifact_uri(artifact, 'jar')
    log.info('[Downloading] JAR from {}'.format(url))
    with open(local_path, 'wb') as fp:
      for chunk in requests_get_check(url).iter_content():
        fp.write(chunk)

  def download_pom(self, artifact):
    """
    Downloads the artifact's POM manifest.
    """

    if not isinstance(artifact, Artifact):
      raise TypeError('expected Artifact')
    if artifact in self.pom_not_found:
      return None
    if artifact in self.pom_cache:
      return self.pom_cache[artifact]

    if not artifact.version:
      if artifact in self.metadata_cache:
        metadata = self.metadata_cache[artifact]
      else:
        metadata_path = self.uri + '/' + artifact.to_maven_metadata()
        response = requests.get(metadata_path)
        if response.status_code != 200:
          return None
        metadata = minidom.parseString(response.content)
        self.metadata_cache[artifact] = metadata
      try:
        latest = metadata.getElementsByTagName('latest')[0].firstChild.nodeValue
      except IndexError:
        latest = metadata.getElementsByTagName('version')[0].firstChild.nodeValue
      artifact.version = latest

    if artifact.is_snapshot():
      snapshot_info = self.get_snapshot_info(artifact)
      if snapshot_info is not None:
        artifact.timestamp, artifact.build_number = snapshot_info

    url = self.get_artifact_uri(artifact, 'pom')
    try:
      log.info('[Checking] POM file {}'.format(url))
      data = requests_get_check(url).text
      self.pom_cache[artifact] = data
      return data
    except requests.exceptions.RequestException:
      self.pom_not_found.add(artifact)
      log.info('[Skipped] POM file not found at {}'.format(url))
      return None

  def get_artifact_uri(self, artifact, ext):
    if not artifact.is_snapshot():
      maven_name = artifact.to_maven_name(ext)
    else:
      maven_name = artifact.to_maven_snapshot_name(ext)
    maven_path = self.uri + '/' + maven_name
    return maven_path

  def get_snapshot_info(self, artifact):
    metadata_path = self.get_metadata_path(artifact)
    try:
      data = requests_get_check(metadata_path).text  # XXX user agent
      eletree = ElementTree.fromstring(data)
      timestamp = eletree.findtext('versioning/snapshot/timestamp')
      build_number = eletree.findtext('versioning/snapshot/buildNumber')
      return (timestamp, build_number)
    except requests.exceptions.RequestException:
      return None

  def get_metadata_path(self, artifact):
    group = artifact.group.replace('.', '/')
    metadata_path = "%s/%s/%s/%s/maven-metadata.xml" % (self.uri, group,
        artifact.artifact, artifact.version)
    return metadata_path


def pom_eval_deps(pom):
  """
  Evaluates the dependencies of a POM XML file.
  """

  if isinstance(pom, str):
    pom = minidom.parseString(pom)

  project = pom.getElementsByTagName('project')[0]

  group_id = None
  artifact_id = None
  version = None
  dependencies = None
  for node in iter_dom_children(project):
    if not version and node.nodeName == 'version':
      version = node.firstChild.nodeValue
    elif not group_id and node.nodeName == 'groupId':
      group_id = node.firstChild.nodeValue
    elif not artifact_id and node.nodeName == 'artifactId':
      artifact_id = node.firstChild.nodeValue
    elif node.nodeName == 'parent':
      for node in iter_dom_children(node):
        if not version and node.nodeName == 'version':
          version = node.firstChild.nodeValue
        elif not group_id and node.nodeName == 'groupId':
          group_id = node.firstChild.nodeValue
        elif not artifact_id and node.nodeName == 'artifactId':
          artifact_id = node.firstChild.nodeValue
    elif not dependencies and node.nodeName == 'dependencies':
      dependencies = node

  if not group_id or not version:
    log.warn('[Error]: could not read version or group_id from POM')
    return []
  if not dependencies:
    return []

  def parse_dependency(node):
    try:
      scope = node.getElementsByTagName('scope')[0].firstChild.nodeValue
    except IndexError:
      scope = 'compile'

    try:
      optional = node.getElementsByTagName('optional')[0].firstChild.nodeValue
    except IndexError:
      optional = False
    else:
      if optional == 'true':
        optional = True
      elif optional == 'false':
        optional = False
      else:
        log.warn('unexpected <optional> value "{}"'.format(optional))
        optional = False

    dep_group = node.getElementsByTagName('groupId')[0].firstChild.nodeValue
    dep_artifact = node.getElementsByTagName('artifactId')[0].firstChild.nodeValue

    try:
      dep_version = node.getElementsByTagName('version')[0].firstChild.nodeValue
    except IndexError:
      dep_version = None

    # Try to resolve some of the properties.
    if dep_group in ('${project.groupId}', '${pom.groupId}'):
      dep_group = group_id
    if dep_version in ('${project.version}', '${pom.version}'):
      dep_version = version

    # We're not a full-blown POM evaluator, so give a warning when
    # we can't handle the property in the dependency version.
    if dep_version and '$' in dep_version:
      msg = 'unable to resolve "{}" in dependency {}:{} ({}:{}:{})'
      log.warn(msg.format(dep_version, dep_group, dep_artifact,
          group_id, artifact_id, version))
      dep_version = None

    return Artifact(dep_group, dep_artifact, dep_version, scope, optional)

  results = []
  for node in iter_dom_children(dependencies):
    if node.nodeName == 'dependency':
      results.append(parse_dependency(node))

  return results


def iter_dom_children(node):
  child = node.firstChild
  while child:
    yield child
    child = child.nextSibling

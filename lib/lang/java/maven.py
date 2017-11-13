"""
Access maven artifacts.
"""

from xml.etree import ElementTree
import xml.dom.minidom as minidom
import requests
import log from 'craftr/utils/log'

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

  def __init__(self, group, artifact, version=None):
    self.group = group
    self.artifact = artifact
    self.version = version
    self.timestamp = None
    self.build_number = None

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
    return 'SNAPSHOT' in self.version

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


class MavenRepository:

  def __init__(self, name, uri):
    self.name = name
    self.uri = uri
    self.pom_cache = {}
    self.pom_not_found = set()

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
    if self.uri.endswith('/'):
      maven_path = self.uri + maven_name
    else:
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
  version = None
  dependencies = None
  for node in iter_dom_children(project):
    if not version and node.nodeName == 'version':
      version = node.firstChild.nodeValue
    elif not group_id and node.nodeName == 'groupId':
      group_id = node.firstChild.nodeValue
    elif node.nodeName == 'parent':
      for node in iter_dom_children(node):
        if not version and node.nodeName == 'version':
          version = node.firstChild.nodeValue
        elif not group_id and node.nodeName == 'groupId':
          group_id = node.firstChild.nodeValue
    elif not dependencies and node.nodeName == 'dependencies':
      dependencies = node

  print('>>>', dependencies)
  if not group_id or not version:
    log.warn('[Error]: could not read version or group_id from POM')
    return []
  if not dependencies:
    return []

  def parse_dependency(node):
    curr_group_id = node.getElementsByTagName('groupId')[0].firstChild.nodeValue
    curr_artifact_id = node.getElementsByTagName('artifactId')[0].firstChild.nodeValue
    curr_version = node.getElementsByTagName('version')[0].firstChild.nodeValue
    if curr_group_id == '${project.groupId}':
      curr_group_id = group_id
    if curr_version == '${project.version}':
      curr_version = version
    return Artifact(curr_group_id, curr_artifact_id, curr_version)

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

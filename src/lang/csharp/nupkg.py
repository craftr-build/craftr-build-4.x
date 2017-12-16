"""
Parse information from .nupkg files.
"""

import xml.dom.minidom
import zipfile
import path from 'craftr/utils/path'


def get_nuspec(nupkg):
  with zipfile.ZipFile(nupkg) as zipf:
    return get_nuspec_from_zipfile_object(zipf)


def get_nuspec_from_zipfile_object(zipf):
  for name in zipf.namelist():
    if name.endswith('.nuspec') and name.find('/', 1) < 0:
      break
  else:
    return None
  return xml.dom.minidom.parse(zipf.open(name))


def nuspec_eval_deps(specdom, target_framework, step='Build'):
  """
  Given a NuSpec DOM (retrieved eg. via #get_nuspec()), this function
  evaluates the items in the `<dependency/>` node. Returns a list of
  #Dependency objects.
  """

  nodes = specdom.getElementsByTagName('dependencies')
  if not nodes:
    return []

  result = []

  def handle_dependency(node):
    exclude = node.getAttribute('exclude')
    if not exclude or step.lower() not in exclude.lower().split(','):
      result.append(Dependency(node.getAttribute('id'), node.getAttribute('version')))

  def handle_group(node):
    if target_framework is None or \
        (node.getAttribute('targetFramework') == target_framework):
      for child in iter_dom_children(node):
        if child.nodeName == 'dependency':
          handle_dependency(child)

  for node in iter_dom_children(nodes[0]):
    if node.nodeName == 'dependency':
      handle_dependency(node)
    elif node.nodeName == 'group':
      handle_group(node)

  return result


def iter_dom_children(node):
  child = node.firstChild
  while child:
    yield child
    child = child.nextSibling


class Dependency:

  def __init__(self, id, version, framework=None):
    while version.count('.') < 2:
      version += '.0'
    self.id = id
    self.version = version
    self.framework = framework or None

  def __str__(self):
    result = '{}:{}'.format(self.id, self.version)
    if self.framework:
      result += '#' + self.framework
    return result

  def __repr__(self):
    return 'nupkg.Dependency(id={!r}, version={!r}, framework={!r})'\
        .format(self.id, self.version, self.framework)

  def __hash__(self):
    return hash(self.as_tuple())

  def __eq__(self, other):
    if isinstance(other, Dependency):
      return self.as_tuple() == other.as_tuple()
    return False

  def as_tuple(self):
    return (self.id, self.version, self.framework)

  def package_dir(self, parent_dir):
    return path.join(parent_dir, self.id + '.' + self.version)

  def subpath(self, parent_dir, *file_path):
    return path.join(self.package_dir(parent_dir), *file_path)

  def nupkg(self, parent_dir):
    return self.subpath(parent_dir, '{}.{}.nupkg'.format(self.id, self.version))

  def resolve(self, parent_dir, framework):
    """
    Resolve the dependency in the specified *package_dir*, returning the
    filename of the `.dll` that matches the specified *framework*. Returns
    #None if the package does not provide a library.
    """

    lib_dir = self.subpath(parent_dir, 'lib')
    if not path.isdir(lib_dir):
      return None
    assembly_dir = path.join(lib_dir, self.framework or framework)
    if not path.isdir(assembly_dir):
      # XXX Resolve to the closest compatible framework, not just this specific one.
      # For now, we'll just sort all the options and take the "highest".
      for name in sorted(path.listdir(lib_dir)):
        assembly_dir = path.join(lib_dir, name)
        if path.isdir(assembly_dir):
          break
      else:
        return None

    return path.join(assembly_dir, '{}.dll'.format(self.id))

  @classmethod
  def from_str(cls, s):
    name, version = s.partition(':')[::2]
    version, framework = version.partition('#')[::2]
    return cls(name, version, framework)

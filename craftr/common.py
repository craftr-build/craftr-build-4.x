
import collections
import re
import sys
from . import path


def match_tag(tag, tags):
  if tag[0] == '!':
    return tag[1:] not in tags
  return tag in tags


class TaggedFile:
  """
  Represents a file attached with zero or more tags.

  This class interns all tag strings.
  """

  def __init__(self, name, tags=()):
    self._name = name
    self._tags = set(sys.intern(x) for x in tags)

  def __repr__(self):
    return 'TaggedFile(name={!r}, tags={{{!r}}})'.format(self.name, ','.join(self.tags))

  def has_tag(self, tag):
    return tag in self._tags

  def add_tags(self, tags):
    self._tags |= set(sys.intern(x) for x in tags)

  @property
  def name(self):
    return self._name

  @property
  def tags(self):
    return set(self._tags)


class FileSet:
  """
  Represents a collection of #TaggedFile objects. Additionally, the #FileSet
  may contain additional variables with lists of strings a values. These may
  not be useful in all contexts.
  """

  def __init__(self):
    self._files = collections.OrderedDict()

  def __repr__(self):
    v = ('{!r}: {!r}'.format(k, v.tags) for k, v in self._files.items())
    return 'FileSet({{{0}}})'.format(', '.join(v))

  def __getitem__(self, name):
    name = path.canonical(name)
    return self._files[name.lower()]

  def __delitem__(self, name):
    name = path.canonical(name)
    del self._files[name]

  def __iter__(self):
    return self._files.values()

  def name(self):
    return self._name

  def add(self, names, tags=()):
    if isinstance(names, str):
      names = [names]
    result = []
    for name in names:
      name = path.canonical(name)
      # We build the hash table using the case-insensitive canonical name.
      name_lower = name.lower()
      obj = self._files.get(name_lower)
      if obj is None:
        obj = TaggedFile(name, tags)
        self._files[name_lower] = obj
      else:
        obj.add_tags(tags)
      result.append(obj)
    return result

  def tagged(self, *tags):
    for tf in self._files.values():
      if not tags or all(match_tag(x, tf.tags) for x in tags):
        yield tf.name

  def to_json(self):
    return {x.name: list(x.tags) for x in self._files.values()}

  @classmethod
  def from_json(cls, data):
    obj = cls()
    for key, tags in data.items():
      obj.add(key,  tags)
    return obj


class ActionVariables:
  """
  A container for variables that must be lists of strings. Used in an
  action's build step together with a #FileSet.
  """

  def __init__(self):
    self._variables = collections.OrderedDict()

  def __repr__(self):
    v = ('{!r}: {!r}'.format(k, v) for k, v in self._variables.items())
    return 'ActionVariables({{{}}})'.format(', '.join(v))

  def __getitem__(self, key):
    return self._variables[key]

  def __setitem__(self, key, value):
    if isinstance(value, str):
      value = [value]
    if not isinstance(value, (list, tuple)):
      raise TypeError('expected str,list/tuple, got {}'.format(type(value).__name__))
    if not all(isinstance(x, str) for x in value):
      raise TypeError('expected item to be str')
    self._variables[key] = list(value)

  def __delitem__(self, key):
    del self._variables[key]

  def __contains__(self, key):
    return key in self._variables

  def get(self, key, default=None):
    return self._variables.get(key, default)

  def to_json(self):
    return self._variables

  @classmethod
  def from_json(cls, data):
    obj = cls()
    obj._variables.update(data)
    return obj


class BuildSet:

  def __init__(self, name, files=None, vars=None):
    self.name = name
    self.files = files or FileSet()
    self.vars = vars or ActionVariables()

  def __repr__(self):
    return 'BuildSet(name={!r}, files={!r}, vars={!r})'.format(
      self.name, self.files, self.vars)

  def to_json(self):
    return {'name': self.name, 'files': self.files.to_json(), 'vars': self.vars.to_json()}

  @classmethod
  def from_json(cls, data):
    return cls(data['name'], FileSet.from_json(data['files']),
      ActionVariables.from_json(data['vars']))

  def subst(self, cmd):
    """
    Substitute all variables references in the list of strings *cmd* with the
    files or variables in this buildset.
    """

    expr = re.compile(r'^(.*)(?:\$\{([^\}]+)\}|\$(\w+))(.*)$')
    result = []
    for string in cmd:
      match = expr.match(string)
      if match:
        px, sx = match.group(1), match.group(4)
        id = match.group(2) or match.group(3)
        tags = [x for x in id.split('&') if x]
        files = list(self.files.tagged(*tags))
        result += [px+x+sx for x in self.files.tagged(*id.split('&'))]
        if len(tags) == 1 and tags[0] in self.vars:
          result += [px+x+sx for x in self.vars[tags[0]]]
      else:
        result.append(string)
    return result

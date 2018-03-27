# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
"""
This module implementations the representation of final build information.
"""

import collections
import hashlib
import json
import nr.path as path
import re
import sys
import warnings

import proplib from './proplib'


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

  def matches(self, tags):
    if isinstance(tags, str):
      tags = [x.strip() for x in tags.split(',')]
    for tag in tags:
      if not tag: continue
      if tag[0] == '!':
        result = tag[1:] not in self._tags
      else:
        result = tag in self._tags
      if not result:
        return False
    return True


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

  def tagged(self, tags):
    if isinstance(tags, str):
      tags = [x.strip() for x in tags.split(',')]
    for tf in self._files.values():
      if tf.matches(tags):
        yield tf.name

  def to_json(self):
    return {x.name: sorted(x.tags) for x in self._files.values()}

  @classmethod
  def from_json(cls, data):
    obj = cls()
    for key, tags in data.items():
      obj.add(key, tags)
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
        tags = match.group(2) or match.group(3)
        if '&' in tags:
          msg = 'legacy tag syntax using `&` character in buildset {!r}: {!r}'
          warnings.warn(msg.format(self.name, tags))
          tags = tags.split('&')
        else:
          tags = tags.split(',')
        files = list(self.files.tagged(tags))
        result += [px+x+sx for x in self.files.tagged(tags)]
        if len(tags) == 1 and tags[0] in self.vars:
          result += [px+x+sx for x in self.vars[tags[0]]]
      else:
        result.append(string)
    return result


class Action:
  """
  Represents an action that translates a set of input files to a set of
  output files. Actions can be used to execute the *commands* multiple
  times for different sets of input/output files. Every action needs at
  least one set of input/output files.

  # Variables
  Every file in an action has a tag associated with it. Files can then be
  accessed by filtering with these tags. To reference files that have a tag,
  use the `$tag` or `${tag}` syntax inside the command list. Multiple tags
  can be separated by `&` characters. Files need all tags specified in a
  variable to match, eg. `${out&dll}` will be expanded to all files that are
  tagged as `out` and `dll`.

  Note that an argument in the command-list will be multiplied for every
  file matching the variable, eg. an argument "-I${include}" may expand to
  multiple arguments like `-Iinclude`, `-Ivendor/optional/include` if there
  are multiple files with the tag `include`.

  Note that only files tagged with `in` and `out` will be considered mandatory
  input and output files for an action. Additionally, the tag `optional` may
  be combined with any of the two tags to specify an optional input or output
  file.

  # Parameters
  target (Target):
    The #Target that this action is generated for. Note that in a session
    where the build graph is loaded from a file and the build modules have
    not been executed, this may be a proxy target with no valid properties.
  name (str):
    The name of the action inside the target.
  commands (list of list of str):
    A list of commands to execute in order. The strings in this list may
    contain variables are described above.
  deps (list of Action):
    A list of actions that need to be executed before this action. This
    relationship should also roughly be represented by the input and output
    files of the actions.
  cwd (str):
    The directory to execute the action in.
  environ (dict of (str, str)):
    An environment dictionary that will be merged on top of the current
    environment before running the commands in the action.
  explicit (bool):
    If #True, this action must be explicitly specified to be built or
    required by another action to be run.
  syncio (bool):
    #True if the action needs to be run with the original stdin/stdout/stderr
    attached.
  deps_prefix (str):
    A string that represents the prefix of for lines in the output of the
    command(s) that represent additional dependencies to the action (eg.
    headers in the case of C/C++). Can not be mixed with *depfile*.
  depfile (str):
    A filename that is produced by the command(s) which lists additional
    dependencies of the action. The file must be formatted like a Makefile.
    Can not be mixed with *deps_prefix*.

  # Members
  builds (list of BuildSet):
    A list of files this action depends on or produces and variables. Both
    are available for variable expansion in the *commands* strings.
  """

  def __init__(self, target, name, deps, commands, cwd=None, environ=None,
               explicit=False, syncio=False, deps_prefix=None, depfile=None):
    assert isinstance(target, str)
    deps = proplib.List[proplib.InstanceOf[Action]]().coerce('deps', deps)
    if deps_prefix and depfile:
      raise TypeError('deps_prefix and depfile parameters can not be mixed')
    self.target = target
    self.name = name
    self.deps =deps
    self.commands = commands
    self.cwd = cwd
    self.environ = environ
    self.explicit = explicit
    self.syncio = syncio
    self.deps_prefix = deps_prefix
    self.depfile = depfile
    self.builds = []

  def __repr__(self):
    return 'Action({!r} with {} buildsets)'.format(
      self.identifier(), len(self.builds))

  def identifier(self):
    return '{}:{}'.format(self.target, self.name)

  def add_buildset(self, buildset=None, name=None):
    if buildset is not None:
      assert isinstance(buildset, BuildSet)
      self.builds.append(buildset)
    else:
      buildset = BuildSet(name)
      self.builds.append(buildset)
    return buildset

  def all_files_tagged(self, tags):
    if isinstance(tags, str):
      tags = [x.strip() for x in tags.split(',')]
    files = []
    for build in self.builds:
      files += build.files.tagged(tags)
    return files

  def to_json(self):
    return {
      'target': self.target,
      'name': self.name,
      'deps': [x.identifier() for x in self.deps],
      'commands': self.commands,
      'cwd': self.cwd,
      'environ': self.environ,
      'explicit': self.explicit,
      'syncio': self.syncio,
      'deps_prefix': self.deps_prefix,
      'depfile': self.depfile,
      'builds': [x.to_json() for x in self.builds]
    }

  @classmethod
  def from_json(cls, data):
    builds = data.pop('builds')
    action = cls(**data)
    action.builds = [BuildSet.from_json(x) for x in builds]
    return action


class BuildGraph:
  """
  This class represents the build graph that is built from #Action#s after
  all targets have been handled.
  """

  def __init__(self):
    self._mtime = sys.maxsize
    self._actions = {}
    self._selected = set()
    # This will be used during deserialization to produce fake #Module
    # objects to associate the #Action#s with.
    self._modules = {}

  def __getitem__(self, action_name):
    return self._actions[action_name]

  def __iter__(self):
    return iter(self._actions.keys())

  def actions(self):
    return self._actions.values()

  def add_action(self, action):
    self._actions[action.identifier()] = action

  def add_actions(self, actions):
    for action in actions:
      self._actions[action.identifier()] = action

  def select(self, action_name):
    if action_name not in self._actions:
      raise KeyError(action_name)
    self._selected.add(action_name)

  def selected(self):
    return (self._actions[x] for x in self._selected)

  def to_json(self):
    root = {}
    root['actions'] = {a.identifier(): a.to_json() for a in self._actions.values()}
    return root

  def from_json(self, root):
    deps = {}
    for action in root['actions'].values():
      action_deps = action.pop('deps')
      action['deps'] = []
      action = Action.from_json(action)
      self._actions[action.identifier()] = action
      deps[action.identifier()] = action_deps
    # Re-establish links between actions.
    for action in self._actions.values():
      for dep in deps[action.identifier()]:
        action.deps.append(self._actions[dep])

  def set_mtime(self, mtime):
    self._mtime = mtime

  def mtime(self):
    return self._mtime

  def hash(self, action):
    hasher = hashlib.md5()
    writer = type('Namespace', (object,), {})()
    writer.write = lambda x: hasher.update(x.encode('utf8'))
    json.dump(action.to_json(), writer, sort_keys=True)
    return hasher.hexdigest()[:12]


class BuildBackend:

  def __init__(self, context, args):
    self.context = context
    self.args = args

  def export(self):
    raise NotImplementedError

  def clean(self, recursive):
    raise NotImplementedError

  def build(self):
    raise NotImplementedError

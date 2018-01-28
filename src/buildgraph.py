
import collections
import hashlib
import itertools
import json
import os
import time
import {stream.concat as concat} from 'craftr/utils'


class IOFiles:
  """
  Represents a set of input, output and optional output files.
  """

  def __init__(self, inputs, outputs, optional_outputs):
    self.inputs = inputs
    self.outputs = outputs
    self.optional_outputs = optional_outputs

  def __repr__(self):
    return '<IOFiles inputs={!r} outputs={!r} optional_outputs={!r}>'.format(
      self.inputs, self.outputs, self.optional_outputs)

  def as_json(self):
    return {
      'inputs': self.inputs,
      'outputs': self.outputs,
      'optional_outputs': self.optional_outputs
    }

  @classmethod
  def from_json(cls, data):
    return cls(**data)


class BuildAction:
  """
  Represents a concrete sequence of system commands.

  # Parameters
  scope (str):
    The scope of the action (this is usually the identifier of the target
    that generated the action).
  name (str):
    The name of the action inside the scope.
  commands (list of list of str):
    A list of commands to execute in order. The variables `$in`, `$out` and
    `$optionalout` are supported. Additionally, a specific index in the list of
    in/out/optionalout files can be accessed using eg. `$out[0]`. The suffix
    can be modified by appending it to the variable like `$out.d` or
    `$out[0].d`.
  deps (list of BuildAction):
    A list of actions that need to be executed before this action. This
    relationship should also roughly be represented by the input and output
    files of the actions.
  cwd (str):
    The directory to execute the action in.
  environ (dict of (str, str)):
    An environment dictionary that will be merged on top of the current
    environment before running the commands in the action.
  foreach (bool):
    If #True, the *commands* are run for every pair of input/output files
    in the *files* list, otherwise the commands will be run once.
  explicit (bool):
    If #True, this action must be explicitly specified to be built or
    required by another action to be run.
  console (bool):
    #True if the action needs to be run with the original stdin/stdout/stderr
    attached.
  input_files (list of str | list of list of str):
    A list of input files or a list of lists of input files. The latter format
    is required with *foreach* set to #True, otherwise the former format
    should be used or the list should contain only one list of input files.
    If this argument is used, it is used together with *output_files* and
    *optional_output_files* to construct the *files* list.
  output_files (list of str | list of list of str):
    If *foreach* is #True, it must have the same length as *input_files*.
  optional_output_files (list of str | list of list of str):
    If *foreach* is #True, it must have the same length as *input_files*.
  files (IOFiles | list of IOFiles):
    A list of #IOFiles objects (required if *foreach* is #True) or a single
    #IOFiles object (only if *foreach* is #False). Can not be mixed with
    *input_files*, *output_files* or *optional_output_files*.
  deps_prefix (str): A string that represents the prefix of for lines
    in the output of the command(s) that represent additional dependencies
    to the action (eg. headers in the case of C/C++). Can not be mixed with
    *depfile*.
  depfile (str): A filename that is produced by the command(s) which lists
    additional dependencies of the action. The file must be formatted like
    a Makefile. Can not be mixed with *deps_prefix*.
  """

  def __init__(self, scope, name, commands,
               deps=None, cwd=None, environ=None, foreach=False,
               explicit=False, console=False, input_files=None,
               output_files=None, optional_output_files=None, files=None,
               deps_prefix=None, depfile=None):
    if not isinstance(scope, str):
      raise TypeError('scope must be str, got {}'.format(type(scope).__name__))
    if not isinstance(name, str):
      raise TypeError('scope must be str, got {}'.format(type(name).__name__))
    if not isinstance(commands, (list, tuple)):
      raise TypeError('commands must be a list/tuple, got {}'.format(
        type(commands).__name__))

    if (input_files is not None or output_files is not None or
        optional_output_files is not None):
      if files is not None:
        raise TypeError('files parameter can not be mixed with '
          'input_files/output_files/optional_output_files')

      input_files = self._normalize_file_list(input_files or [], foreach)
      output_files = self._normalize_file_list(output_files or [], foreach)
      optional_output_files = self._normalize_file_list(optional_output_files or [], foreach)
      files = []

      if foreach:
        sizes = set(len(x) for x in (input_files, output_files, optional_output_files))
        if 0 in sizes: sizes.remove(0)
        if len(sizes) not in (0, 1):
          raise ValueError('incompatible input_files ({}), output_files ({}) '
              'optional_output_files ({}) lengths for foreach BuildAction'
            .format(len(input_files), len(output_files),
              len(optional_output_files))
          )
      files = [
        IOFiles(a, b, c) for a, b, c in
        itertools.zip_longest(
          input_files, output_files, optional_output_files,
          fillvalue=[])
      ]
    else:
      if not foreach and not isinstance(files, (list, tuple)):
        files = [files]
      if not all(isinstance(x, IOFiles) for x in files):
        raise TypeError('files must be a List[IOFiles] or IOFiles, got {}'
          .format(set(type(x).__name__ for x in files)))

    if depfile and deps_prefix:
      raise ValueError('can not mix depfile and deps_prefix parameter')

    self.scope = scope
    self.name = name
    self.commands = commands
    self.files = files
    self.deps = deps
    self.cwd = cwd
    self.environ = environ
    self.foreach = foreach
    self.explicit = explicit
    self.console = console
    self.deps_prefix = deps_prefix
    self.depfile = depfile

  def __repr__(self):
    return '<BuildAction {!r}>'.format(self.identifier())

  def identifier(self):
    return '{}#{}'.format(self.scope, self.name)

  def get_output_files(self):
    return list(concat(x.outputs for x in self.files))

  def as_json(self):
    result = vars(self).copy()
    if result['deps'] and isinstance(result['deps'][0], BuildAction):
      result['deps'] = [x.identifier() for x in self.deps]
    result['files'] = [x.as_json() for x in self.files]
    return result

  @classmethod
  def from_json(cls, data, nodes=None):
    if nodes is not None:
      data['deps'] = [nodes[x] for x in data['deps']]
    data['files'] = [IOFiles.from_json(x) for x in data['files']]
    return cls(**data)

  @staticmethod
  def _normalize_file_list(lst, foreach):
    """
    Normalizes a list of filenames. This will result in a `List[List[str]]`.
    If *foreach* is #False, there will be exactly one item in the returned
    list, that matches the files in *lst*.
    """

    result = [] if foreach else [[]]
    for item in lst:
      if foreach:
        if isinstance(item, str):
          item = [item]
        if not isinstance(item, (list, tuple)):
          raise ValueError('expected List[^List[str]]-like, got {!r}'.format(item))
        if not all(isinstance(x, str) for x in item):
          raise ValueError('expected List[List[^str]], got {!r}'.format(item))
        result.append(item)
      else:
        if not isinstance(item, str):
          raise ValueError('expected List[^str], got {}'.format(type(item).__name__))
        result[-1].append(item)
    return result


class BaseBuildGraph:

  def __getitem__(self, key):
    raise NotImplementedError

  def hash(self, action):
    """
    Generate a hash for an action in the #BuildGraph.
    """

    data = json.dumps(action.as_json(), sort_keys=True)
    return hashlib.sha1(data.encode('utf8')).hexdigest()[:12]


class BuildGraph(BaseBuildGraph):
  """
  Represents the actions generated by targets in a more easily accessible
  datastructure, which also supports saving to and loading from disk.
  """

  def __init__(self):
    self._actions = {}
    self._scopes = {}
    self._selected = []
    self._mtime = time.time()

  def __getitem__(self, key):
    """
    Retrieve an action by its full identifier.
    """

    return self._actions[key]

  def from_actions(self, actions):
    """
    Fill the #BuildGraph from the iterable *actions* which contains only
    #BuildAction objects.
    """

    for action in actions:
      self._actions[action.identifier()] = action
      self._scopes.setdefault(action.scope, []).append(action)
    return self

  def from_json(self, data):
    """
    Fills the #BuildGraph from the JSON representation *data*.
    """

    for key, value in data['actions'].items():
      value = value.copy()
      value['deps'] = []
      action = BuildAction.from_json(value)
      self._actions[key] = action
    for key, value in data['actions'].items():
      self._actions[key].deps = [self._actions[x] for x in value['deps']]
    self._scopes.update({k: [self._actions[x] for x in v] for k, v in data['scopes'].items()})

  def as_json(self):
    """
    Converts the #BuildGraph to a JSON representation which can be saved to
    disk using #json.dump() and loaded back using #json.load() and the
    #from_json() method.
    """

    return {
      'actions': {x.identifier(): x.as_json() for x in self._actions.values()},
      'scopes': {k: [action.identifier() for action in scope]
                    for k, scope in self._scopes.items()}
    }

  def read(self, filename):
    """
    Loads the #BuildGraph from a JSON representation previously saved with
    #write(). Note that this method will update the #mtime of the graph.
    """

    with open(filename, 'r') as fp:
      self.from_json(json.load(fp))
    self._mtime = os.path.getmtime(filename)
    return self

  def write(self, filename):
    """
    Writes the #BuildGraph to the specified *filename* in JSON format.
    """

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as fp:
      json.dump(self.as_json(), fp, indent=2, sort_keys=True)

  def actions(self):
    """
    Iterable for all actions in the #BuildGraph.
    """

    return self._actions.values()

  def dotviz(self, fp):
    """
    Outputs a Dotviz markup for the #BuildGraph.
    """

    fp.write('digraph "craftr" {\n')
    for node in self.actions():
      fp.write('\t{} [label="{}" shape="round" style="rounded"];\n'.format(id(node), node.identifier()))
      for dep in node.deps:
        fp.write('\t\t{} -> {};\n'.format(id(dep), id(node)))
    fp.write('}\n')

  def select(self, *actions):
    """
    Marks one or more actions in the graph as selected. The selected actions
    can be retrieved using the #selected() method. Parameters passed to this
    function may either be #BuildAction instances, or strings that either
    identify a #BuildAction or a scope.
    """

    for action in actions:
      if isinstance(action, BuildAction):
        self._selected.append(action.identifier())
      elif action in self._actions:
        self._selected.append(action)
      elif action in self._scopes:
        self._selected.extend(x.identifier() for x in self._scopes[action])
      else:
        raise ValueError(action)

  def deselect_all(self):
    """
    Deselects all actions in the graph.
    """

    self._selected = []

  def selected(self):
    """
    Returns a generator that yields all selected actions.
    """

    return (self[k] for k in self._selected)

  def mtime(self):
    """
    Returns the last modification time of the #BuildGraph. If read from a
    file, the value will equal the modification time of the file.
    """

    return self._mtime

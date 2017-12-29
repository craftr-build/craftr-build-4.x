"""
Public build-script API of the Craftr build system.
"""

import {Configuration} from './utils/cfgparser'
import path from './utils/path'

#: Set to True when `craftr --configure` is executed.
is_configure = False

#: Set to True when this is a release build.
is_release = False

#: Set to the build directory.
build_directory = None

#: This is a persistent cache that is serialized into JSON. All objects in
#: this dictionary must be JSON serializable.
cache = {}

#: Craftr configuration, automatically loaded from the configuration file
#: by the CLI.
options = Configuration()

import {
  resolve as resolve_target,
  Namespace,
  Target,
  Behaviour,
  BuildAction,
  Factory
  } from './target'
import {BuildGraph} from './buildgraph'


def localpath(p):
  """
  Returns the canonical representation of the path *p*. If *p* is a relative
  path, it will be considered relative to the current module's directory.
  """

  if path.isrel(p):
    p = path.join(str(require.current.directory), p)
  return path.canonical(p)


def glob(patterns, parent=None, excludes=None):
  """
  Same as #path.glob(), except that *parent* defaults to the parent directory
  of the currently executed module (not always the same directory as the cell
  base directory!).
  """

  if not parent:
    parent = str(require.current.directory)
  return path.glob(patterns, parent, excludes)


def relocate_files(files, outdir, suffix, replace_suffix=True, parent=None):
  """
  Converts the list of filenames *files* so that they are placed under
  *outdir* instead of *parent* and have the specified *suffix*. If
  *replace_suffix* is #True (default), then the file's suffix will be
  replaced, otherwise appended.

  If *parent* is not specified, the directory of the current cell is used.
  """

  if parent is None:
    parent = cell().directory
  outdir = path.canonical(outdir)
  parent = path.canonical(parent)

  result = []
  for filename in files:
    filename = path.join(outdir, path.rel(path.canonical(filename), parent))
    filename = path.addsuffix(filename, suffix, replace=replace_suffix)
    result.append(filename)

  return result


class Gentarget(Behaviour):

  def init(self, commands, environ=None, cwd=None, input_files=(), output_files=()):
    self.commands = commands
    self.environ = environ
    self.cwd = cwd
    self.input_files = input_files
    self.output_files = output_files

  def add_additional_args(self, args):
    """
    The default build backend calls this function when additional command-line
    arguments are specified for this specific target.
    """

    self.commands[-1].extend(args)

  def translate(self):
    self.target.add_action(
      None, self.commands, cwd=self.cwd, environ=self.environ,
      input_files=self.input_files, output_files=self.output_files
    )


gentarget = Factory(Gentarget)

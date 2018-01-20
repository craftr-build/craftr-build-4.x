"""
Public build-script API of the Craftr build system.
"""

import re
import requests
import posixpath
import tarfile
import zipfile

import {Configuration} from './utils/cfgparser'
import path from './utils/path'
import sh from './utils/sh'
import utils from './utils'

#: Verbose output enabled/disabled.
verbose = False

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


def fmt(s, frame=None):
  """
  Formats the string *s* with the variables from the parent frame or the
  specified frame-object *frame*.
  """

  import inspect
  import gc
  import types
  class Resolver:
    def __init__(self, frame):
      self.frame = frame
      self._func = NotImplemented
    @property
    def func(self):
      if self._func is NotImplemented:
        self._func = next(filter(lambda x: isinstance(x, types.FunctionType),
            gc.get_referrers(self.frame.f_code)), None)
      return self._func
    def __getitem__(self, key):
      # Try locals
      try: return self.frame.f_locals[key]
      except KeyError: pass
      # Try non-locals
      try:
        index = self.frame.f_code.co_freevars.index(key)
      except ValueError:
        pass
      else:
        if self.func:
          x = self.func.__closure__[index]
          return x
      # Try globals
      try: return self.frame.f_globals[key]
      except KeyError: pass

  frame = frame or inspect.currentframe().f_back
  vars = Resolver(frame)
  return s.format_map(vars)


def localpath(*p):
  """
  Returns the canonical representation of the path *p*. If *p* is a relative
  path, it will be considered relative to the current module's directory.
  """

  p = path.join(*p)
  if path.isrel(p):
    p = path.join(Namespace.current().directory, p)
  return path.canonical(p)


def buildlocal(*p):
  p = path.join(*p)
  if path.isrel(p):
    p = path.join(Namespace.current().build_directory, p)
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
    parent = Namespace.current().directory
  outdir = path.canonical(outdir)
  parent = path.canonical(parent)

  result = []
  for filename in files:
    filename = path.join(outdir, path.rel(path.canonical(filename), parent))
    filename = path.addsuffix(filename, suffix, replace=replace_suffix)
    result.append(filename)

  return result


def get_source_archive(url):
  """
  Downloads an archive from the specified *URL* and extracts it. Returns the
  path to the unpacked directory.
  """

  archive_cache = cache.setdefault('get_source_archive', {})
  directory = archive_cache.get(url)
  if directory and path.isdir(directory):
    return directory

  filename = posixpath.basename(url)
  response = requests.get(url, stream=True)
  if 'Content-Disposition' in response.headers:
    hdr = response.headers['Content-Disposition']
    filename = re.findall("filename=(.+)", hdr)[0]

  directory = path.join(build_directory, '.source-downloads', path.rmvsuffix(filename))

  print('Downloading {} ...'.format(url))
  response.raise_for_status()
  with utils.tempfile(suffix=filename) as fp:
    for chunk in response.iter_content(16*1024):
      fp.write(chunk)
    fp.close()
    path.makedirs(directory)
    print('Extracting to {} ...'.format(directory))
    if filename.endswith('.zip'):
      with zipfile.ZipFile(fp.name) as zipf:
        zipf.extractall(directory)
    else:
      with tarfile.open(fp.name) as tarf:
        tarf.extractall(directory)

  archive_cache[url] = directory
  return directory


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

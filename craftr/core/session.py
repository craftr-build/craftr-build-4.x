# The Craftr build system
# Copyright (C) 2016  Niklas Rosenstein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
:mod:`craftr.core.session`
==========================

This module provides the :class:`Session` class which manages the loading
process of Craftr modules and contains all the important root datastructures
for the meta build process (such as a :class:`craftr.core.build.Graph`).
"""

from craftr.core import build, manifest, renames
from craftr.core.logging import logger
from craftr.core.manifest import Manifest
from craftr.utils import argspec, path
from nr.types.version import Version, VersionCriteria

import json
import os
import tempfile
import types
import werkzeug

MANIFEST_FILENAME = 'manifest.json'


class ModuleNotFound(Exception):

  def __init__(self, name, version):
    self.name = name
    self.version = version

  def __str__(self):
    if isinstance(self.version, Version):
      return '{}[={}]'.format(self.name, self.version)
    else:
      return '{}[{}]'.format(self.name, self.version)


class InvalidOption(Exception):

  def __init__(self, module, errors):
    self.module = module
    self.errors = errors

  def __str__(self):
    return '\n'.join(self.format_errors())

  def format_errors(self):
    for option, value, exc in self.errors:
      yield '{}.{} ({}): {}'.format(self.module.manifest.name, option.name,
          self.module.manifest.version, exc)


class Session(object):
  """
  This class manages the :class:`build.Graph` and loading of Craftr modules.

  .. attribute:: graph

    A :class:`build.Graph` instance.

  .. attribute:: path

    A list of paths that will be searched for Craftr modules.

  .. attribute:: require

    An instance of :class:`Require` that is used to load other Craftr
    modules conveniently.

  .. attribute:: module

    The Craftr module that is currently being executed. This is an instance
    of the :class:`Module` class and the same as the tip of the
    :attr:`modulestack`.

  .. attribute:: modulestack

    A list of modules where the last element (tip) is the module that is
    currently being executed.

  .. attribute:: modules

    A nested dictionary that maps from name to a dictionary of version
    numbers mapping to :class:`Module` objects. These are the modules that
    have already been loaded into the session or that have been found and
    cached but not yet been executed.

  .. attribute:: maindir

    The main directory from which Craftr was run. Craftr will switch to the
    build directory at a later point, which is why we keep this member for
    reference.

  .. attribute:: builddir

    The absolute path to the build directory.

  .. attribute:: options

    A dictionary of options that are passed down to Craftr modules.

  .. attributes:: cache

    A JSON object that will be loaded from the current workspace's cache
    file and written back when Craftr exits without errors. The cache can
    contain anything and can be modified by everything, however it should
    be assured that no name conflicts and accidental modifications/deletes
    occur.

    Reserved keywords in the cache are ``"build"`` and ``"loaders"``.
  """

  #: The current session object. Create it with :meth:`start` and destroy
  #: it with :meth:`end`.
  current = None

  #: Diretory that contains the Craftr standard library.
  stl_dir = path.norm(path.join(__file__, '../../stl'))
  stl_auxiliary_dir = path.norm(path.join(__file__, '../../stl_auxiliary'))

  def __init__(self, maindir=None):
    self.maindir = path.norm(maindir or path.getcwd())
    self.builddir = path.join(self.maindir, 'build')
    self.graph = build.Graph()
    self.path = [self.stl_dir, self.stl_auxiliary_dir, self.maindir,
        path.join(self.maindir, 'craftr/modules')]
    self.modulestack = []
    self.modules = {}
    self.options = {}
    self.cache = {}
    self._tempdir = None
    self._manifest_cache = {}  # maps manifest_filename: manifest
    self._refresh_cache = True

  def __enter__(self):
    if Session.current:
      raise RuntimeError('a session was already created')
    Session.current = self
    return Session.current

  def __exit__(self, exc_value, exc_type, exc_tb):
    if Session.current is not self:
      raise RuntimeError('session not in context')
    if self._tempdir and not self.options.get('craftr.keep_temporary_directory'):
      logger.debug('removing temporary directory:', self._tempdir)
      try:
        path.remove(self._tempdir, recursive=True)
      except OSError as exc:
        logger.debug('error:', exc, indent=1)
      finally:
        self._tempdir = None
    Session.current = None

  @property
  def module(self):
    if self.modulestack:
      return self.modulestack[-1]
    return None

  def read_cache(self, fp):
    cache = json.load(fp)
    if not isinstance(cache, dict):
      raise ValueError('Craftr Session cache must be a JSON object, got {}'
          .format(type(cache).__name__))
    self.cache = cache

  def write_cache(self, fp):
    json.dump(self.cache, fp, indent='\t')

  def expand_relative_options(self, main_module):
    """
    After the main module has been detected, relative option names (starting
    with ``.``) should be converted to absolute option names. This is what
    the method does.

    :param main_module: The name of the main module.
    """

    for key in tuple(self.options.keys()):
      if key.startswith('.'):
        self.options[main_module + key] = self.options.pop(key)

  def get_temporary_directory(self):
    """
    Returns a writable temporary directory that is primarily used by loaders
    to store temporary files. The temporary directory will be deleted when
    the Session context ends unless the ``craftr.keep_temporary_directory``
    option is set.

    :raise RuntimeError: If the session is not currently in context.
    """

    if Session.current is not self:
      raise RuntimeError('session not in context')
    if not self._tempdir:
      self._tempdir = path.join(self.builddir, '.temp')
      logger.debug('created temporary directory:', self._tempdir)
    return self._tempdir

  def parse_manifest(self, filename):
    """
    Parse a manifest by filename and add register the module to the module
    cache. Returns the :class:`Module` object. If the manifest has already
    been parsed, it will not be re-parsed.

    :raise Manifest.Invalid: If the manifest is invalid.
    :return: :const:`None` if the manifest is a duplicate of an already
      parsed manifest (determined by name and version), otherwise the
      :class:`Module` object for the manifest's module.
    """

    filename = path.norm(path.abs(filename))
    if filename in self._manifest_cache:
      manifest = self._manifest_cache[filename]
      return self.find_module(manifest.name, manifest.version)

    manifest = Manifest.parse(filename)
    self._manifest_cache[filename] = manifest
    versions = self.modules.setdefault(manifest.name, {})
    if manifest.version in versions:
      logger.debug('multiple occurences of "{}-{}" found, '
          'one of which is located at "{}"'.format(manifest.name,
          manifest.version, filename))
      module = None
    else:
      logger.debug('parsed manifest: {}-{} ({})'.format(
          manifest.name, manifest.version, filename))
      module = Module(path.dirname(filename), manifest)
      versions[manifest.version] = module

    return module

  def update_manifest_cache(self, force=False):
    if not self._refresh_cache and not force:
      return
    self._refresh_cache = False

    for directory in self.path:
      choices = []
      choices.append(path.join(directory, MANIFEST_FILENAME))
      for item in path.easy_listdir(directory):
        choices.append(path.join(directory, item, MANIFEST_FILENAME))
        choices.append(path.join(directory, item, 'craftr', MANIFEST_FILENAME))

      for filename in map(path.norm, choices):
        if filename in self._manifest_cache:
          continue  # don't parse a manifest that we already parsed
        if not path.isfile(filename):
          continue
        try:
          self.parse_manifest(filename)
        except Manifest.Invalid as exc:
          logger.warn('invalid manifest found:', filename)
          logger.warn(exc, indent=1)

  def find_module(self, name, version):
    """
    Finds a module in the :attr:`path` matching the specified *name* and
    *version*.

    :param name: The name of the module.
    :param version: A :class:`VersionCriteria`, :class:`Version` or string
      in a VersionCritiera format.
    :raise ModuleNotFound: If the module can not be found.
    :return: :class:`Module`
    """

    argspec.validate('name', name, {'type': str})
    argspec.validate('version', version, {'type': [str, Version, VersionCriteria]})

    if name in renames.renames:
      logger.warn('"{}" is deprecated, use "{}" instead'.format(
          name, renames.renames[name]))
      name = renames.renames[name]

    if isinstance(version, str):
      try:
        version = Version(version)
      except ValueError as exc:
        version = VersionCriteria(version)

    self.update_manifest_cache()
    if name in self.modules:
      if isinstance(version, Version):
        if version in self.modules[name]:
          return self.modules[name][version]
        raise ModuleNotFound(name, version)
      for module in sorted(self.modules[name].values(),
          key=lambda x: x.manifest.version, reverse=True):
        if version(module.manifest.version):
          return module

    raise ModuleNotFound(name, version)


class Module(object):
  """
  This class represents a Craftr module that has been or is currently being
  executed. Every module has a project directory and a manifest with some
  basic information on the module such as its name, version, but also things
  like its dependencies and options.

  Every Craftr project (i.e. module) contains a ``manifest.json`` file
  and the main ``Craftrfile``.

  ::

    myproject/
      include/
      source/
      Craftrfile
      manifest.json

  .. attribute:: directory

    The directory that contains the ``manifest.json``. Note that the actual
    project directory depends on the :attr:`Manifest.project_dir` member.

  .. attribute:: ident

    A concentation of the name and version defined in the :attr:`manifest`.

  .. attribute:: project_dir

    Path to the project directory as specified in the :attr:`manifest`.

  .. attribute:: manifest

  .. attribute:: namespace

  .. attribute:: executed

    True if the module was executed with :meth:`run`.

  .. attribute:: options

    A :class:`~craftr.core.manifest.Namespace` that contains all the options
    for the module. This member is only initialized when the module is run
    or with :meth:`init_options`.
  """

  NotFound = ModuleNotFound
  InvalidOption = InvalidOption

  def __init__(self, directory, manifest):
    self.directory = directory
    self.manifest = manifest
    self.namespace = types.ModuleType(self.manifest.name)
    self.executed = False
    self.options = None

  def __repr__(self):
    return '<craftr.core.session.Module "{}-{}">'.format(self.manifest.name,
      self.manifest.version)

  @property
  def ident(self):
    return '{}-{}'.format(self.manifest.name, self.manifest.version)

  @property
  def project_dir(self):
    return path.norm(path.join(self.directory, self.manifest.project_dir))

  def init_options(self, recursive=False, _break_recursion=None):
    """
    Initialize the :attr:`options` member. Requires an active session context.

    :param recursive: Initialize the options of all dependencies as well.
    :raise InvalidOption: If one or more options are invalid.
    :raise ModuleNotFound: If *recursive* is specified and a dependency
      was not found.
    :raise RuntimeError: If there is no current session context.
    """

    if not session:
      raise RuntimeError('no current session')
    if _break_recursion is self:
      return

    if recursive:
      for name, version in self.manifest.dependencies.items():
        module = session.find_module(name, version)
        module.init_options(True, _break_recursion=self)

    if self.options is None:
      errors = []
      self.options = self.manifest.get_options_namespace(session.options, errors)
      if errors:
        self.options = None
        raise InvalidOption(self, errors)

  def run(self):
    """
    Loads the code of the main Craftr build script as specified in the modules
    manifest and executes it. Note that this must occur in a context where
    the :data:`session` is available.

    :raise RuntimeError: If there is no current :data:`session` or if the
      module was already executed.
    """

    if not session:
      raise RuntimeError('no current session')
    if self.executed:
      raise RuntimeError('already run')

    self.executed = True
    self.init_options()

    script_fn = path.norm(path.join(self.directory, self.manifest.main))
    with open(script_fn) as fp:
      code = compile(fp.read(), script_fn, 'exec')

    vars(self.namespace).update(self.get_init_globals())
    self.namespace.__file__ = script_fn
    self.namespace.__name__ = self.manifest.name
    self.namespace.__version__ = str(self.manifest.version)
    try:
      session.modulestack.append(self)
      exec(code, vars(self.namespace))
    finally:
      assert session.modulestack.pop() is self

  def get_init_globals(self):
    """
    Returns a dictionary initialized with the default built-in values for a
    build script.
    """

    from craftr import defaults
    result = {}
    for key, value in vars(defaults).items():
      if not key.startswith('_'):
        result[key] = value
    result.update({
      'options': self.options,
      'project_dir': self.project_dir
    })
    return result


#: Proxy object that points to the current :class:`Session` object.
session = werkzeug.LocalProxy(lambda: Session.current)

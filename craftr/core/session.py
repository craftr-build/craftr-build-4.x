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

from craftr.core import build, manifest
from craftr.core.logging import logger
from craftr.core.manifest import Manifest, LoaderContext
from craftr.utils import argspec, path
from nr.types.version import Version, VersionCriteria

import os
import types
import werkzeug


class ModuleNotFound(Exception):

  def __init__(self, name, version):
    self.name = name
    self.version = version

  def __str__(self):
    if isinstance(self.version, Version):
      return '{}-{}'.format(self.name, self.version)
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


class LoaderCacheError(Exception):

  def __init__(self, module, message):
    self.module = module
    self.message = message

  def __str__(self):
    return '"{}" -- {}'.format(self.module.ident, self.message)


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

  .. attribute:: options

    A dictionary of options that are passed down to Craftr modules.

  .. attributes:: cache

    A JSON object that will be loaded from the current workspace's cache
    file and written back when Craftr exits without errors. The cache can
    contain anything and can be modified by everything, however it should
    be assured that no name conflicts and accidental modifications/deletes
    occur.

    Currently the cache is mainly used for loaders. The information is saved
    in the ``'loaders'`` key.

    .. code:: json

      {
        "loaders": {
          "modulename-1.0.0": {
            "name": "source",
            "data": {"directory": "..."}
          }
        }
      }

  .. attribute:: tempdir

    Temporary directory, primarily used for loader data.
  """

  #: The current session object. Create it with :meth:`start` and destroy
  #: it with :meth:`end`.
  current = None

  @staticmethod
  def start(*args, **kwargs):
    if Session.current:
      raise RuntimeError('a session was already created')
    Session.current = Session(*args, **kwargs)
    return Session.current

  @staticmethod
  def end():
    Session.current = None

  def __init__(self, maindir=None):
    self.maindir = maindir or path.getcwd()
    self.graph = build.Graph()
    self.path = [self.maindir, path.join(self.maindir, 'craftr/modules')]
    self.modulestack = []
    self.modules = {}
    self.options = {}
    self.cache = {'loaders': {}}
    self.tempdir = path.join(self.maindir, 'craftr/.temp')
    self._manifest_cache = {}  # maps manifest_filename: manifest
    self._refresh_cache = True

  @property
  def module(self):
    if self.modulestack:
      return self.modulestack[-1]
    return None

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
      logger.debug('parsed manifest for {}-{}'.format(
          manifest.name, manifest.version))
      module = Module(path.dirname(filename), manifest)
      versions[manifest.version] = module

    return module

  def update_manifest_cache(self, force=False):
    if not self._refresh_cache and not force:
      return
    self._refresh_cache = False

    logger.debug('Session: refreshing module cache...')
    logger.indent()
    for directory in self.path:
      for item in path.easy_listdir(directory):
        manifest_fn = path.join(directory, item, 'craftr', 'manifest.json')
        manifest_fn = path.norm(manifest_fn)
        if manifest_fn in self._manifest_cache:
          continue  # don't parse a manifest that we already parsed
        if not path.isfile(manifest_fn):
          continue
        try:
          self.parse_manifest(manifest_fn)
        except Manifest.Invalid as exc:
          logger.debug('invalid manifest found at "{}": {}'
              .format(manifest_fn, exc), indent=1)
    logger.dedent()

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

  Every Craftr project (i.e. module) contains a directory named ``craftr/``
  that contains the ``manifest.json`` file, the main ``Craftrfile`` and so
  on. The project directory in return is usually the directory above that
  ``craftr/`` directory.

  ::

    myproject/
      craftr/
        manifest.json
        Craftrfile
      source/
      include/

  .. attribute:: directory

    The directory that contains the ``manifest.json``. Note that the actual
    project directory depends on the :attr:`Manifest.project_directory` member.

  .. attribute:: ident

    A concentation of the name and version defined in the :attr:`manifest`.

  .. attribute:: project_directory

    Path to the project directory as specified in the :attr:`manifest`.

  .. attribute:: manifest

  .. attribute:: namespace

  .. attribute:: executed

    True if the module was executed with :meth:`run`.

  .. attribute:: options

    A :class:`~craftr.core.manifest.Namespace` that contains all the options
    for the module. This member is only initialized when the module is run
    or with :meth:`init_options`.

  .. attribute:: loader

    The loader that was specified in the manifest and initialized with
    :meth:`init_loader`.
  """

  NotFound = ModuleNotFound
  InvalidOption = InvalidOption

  def __init__(self, directory, manifest):
    self.directory = directory
    self.manifest = manifest
    self.namespace = types.ModuleType(self.manifest.name)
    self.executed = False
    self.options = None
    self.loader = None

  def __repr__(self):
    return '<craftr.core.session.Module "{}-{}">'.format(self.manifest.name,
      self.manifest.version)

  @property
  def ident(self):
    return '{}-{}'.format(self.manifest.name, self.manifest.version)

  @property
  def project_directory(self):
    return path.norm(path.join(self.directory, self.manifest.project_directory))

  def init_options(self):
    """
    Initialize the :attr:`options` member. Requires an active session context.

    :raise InvalidOption: If one or more options are invalid.
    :raise RuntimeError: If there is no current session context.
    """

    if not session:
      raise RuntimeError('no current session')
    if self.options is None:
      errors = []
      self.options = self.manifest.get_options_namespace(session.options, errors)
      if errors:
        self.options = None
        raise InvalidOption(self, errors)

  def init_loader(self):
    """
    Initialize the loader with the information that is stored in the sessions
    loader cache. Note that the loader must be selected in an additional step
    to prepare the loader cache.

    :raise NoLoaderCacheAvailable: If there is no loader cache for this
      module in the sessions cache.
    :raise RuntimeError: If there is no current session context.
    """

    if not session:
      raise RuntimeError('no current session')
    if not self.manifest.loaders:
      return
    if self.loader is None:
      if self.ident not in session.cache['loaders']:
        raise LoaderCacheError(self, 'no loader cache available')
      cache = session.cache['loaders'][self.ident]
      loader = [l for l in self.manifest.loaders if l.name == cache['name']]
      if not loader:
        raise LoaderCacheError(self, 'inconistent cache -- has no loader "{}"'
            .format(cache['name']))
      loader[0].init_cache(cache['data'])
      self.loader = loader[0]

  def run_loader(self):
    """
    This function is used outside of the build step to initialize the cache
    of loader objects in this module.
    """

    #argspec.validate('context', context, {'type': LoaderContext})

    self.init_options()
    if self.loader is not None or not self.manifest.loaders:
      return

    logger.info('finding loader for "{}" ...'.format(self.ident))
    context = LoaderContext(session.maindir, self.manifest, self.options,
        session.tempdir, session.tempdir)
    for loader in self.manifest.loaders:
      try:
        cache_data = loader.load(context)
      except manifest.LoaderError as exc:
        pass
      else:
        session.cache['loaders'][self.ident] = {
            'name': loader.name, 'data': cache_data}
        break

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
    self.init_loader()
    self.init_options()

    script_fn = path.norm(path.join(self.directory, self.manifest.main))
    script_fn = path.rel(script_fn, session.maindir, nopar=True)
    with open(script_fn) as fp:
      code = compile(fp.read(), script_fn, 'exec')

    from craftr import defaults
    for key, value in vars(defaults).items():
      if not key.startswith('_'):
        vars(self.namespace)[key] = value
    vars(self.namespace).update({
      '__file__': script_fn,
      '__name__': self.manifest.name,
      '__version__': str(self.manifest.version),
      'options': self.options,
      'loader': self.loader,
      'project_dir': self.project_directory,
    })

    try:
      session.modulestack.append(self)
      exec(code, vars(self.namespace))
    finally:
      assert session.modulestack.pop() is self


def iter_module_hierarchy(session, module):
  yield module
  for name, criteria in module.manifest.dependencies.items():
    yield from iter_module_hierarchy(session, session.find_module(name, criteria))


#: Proxy object that points to the current :class:`Session` object.
session = werkzeug.LocalProxy(lambda: Session.current)

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

from craftr.core import build
from craftr.core.logging import logger
from craftr.core.manifest import Manifest
from craftr.utils import argspec, path
from nr.types.version import Version, VersionCriteria

import os
import werkzeug


class ModuleNotFound(Exception):
  pass


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
    self.graph = build.Graph()
    self.path = ['.', 'craftr/modules']
    self.modulestack = []
    self.modules = {}
    self.maindir = maindir or path.getcwd()
    self._manifest_cache = {}  # maps manifest_filename: manifest
    self._refresh_cache = True

  @property
  def module(self):
    if self.modulestack:
      return self.modulestack[-1]
    return None

  def update_manifest_cache(self, force=False):
    if not self._refresh_cache and not force:
      return
    self._refresh_cache = False

    logger.debug('Session: refreshing module cache...')
    for directory in self.path:
      for item in path.easy_listdir(directory):
        manifest_fn = path.join(directory, item, 'craftr', 'manifest.json')
        manifest_fn = path.norm(manifest_fn)
        if manifest_fn in self._manifest_cache:
          continue  # don't parse a manifest that we already parsed
        if not path.isfile(manifest_fn):
          continue
        try:
          manifest = Manifest.parse(manifest_fn)
        except Manifest.Invalid as exc:
          logger.debug('invalid manifest found at "{}": {}'
              .format(manifest_fn, exc), indent=1)
        else:
          self._manifest_cache[manifest_fn] = manifest
          versions = self.modules.setdefault(manifest.name, {})
          if manifest.version in versions:
            logger.debug('multiple occurences of "{}-{}" found, '
                'one of which is located at "{}"'.format(manifest.name,
                manifest.version, manifest_fn), indent=1)
          else:
            logger.debug('[+] {}-{}'.format(
                manifest.name, manifest.version), indent=1)
            versions[manifest.version] = Module(
                path.dirname(manifest_fn), manifest)

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

  .. attribute:: project_directory

    Path to the project directory as specified in the :attr:`manifest`.

  .. attribute:: manifest

  .. attribute:: namespace

  .. attribute:: executed

    True if the module was executed with :meth:`run`.
  """

  def __init__(self, directory, manifest):
    self.directory = directory
    self.manifest = manifest
    self.namespace = {}
    self.executed = False

  def __repr__(self):
    return '<craftr.core.session.Module "{}-{}">'.format(self.manifest.name,
      self.manifest.version)

  @property
  def project_directory(self):
    return path.norm(path.join(self.directory, self.manifest.project_directory))

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
    script_fn = path.norm(path.join(self.directory, self.manifest.main))
    script_fn = path.rel(script_fn, session.maindir, nopar=True)
    with open(script_fn) as fp:
      code = compile(fp.read(), script_fn, 'exec')

    from craftr import defaults
    for key, value in vars(defaults).items():
      if not key.startswith('_'):
        self.namespace[key] = value
    self.namespace.update({
      '__file__': script_fn,
      '__name__': self.manifest.name,
      '__version__': str(self.manifest.version),
      'project_dir': self.project_directory,
    })

    exec(code, self.namespace)

#: Proxy object that points to the current :class:`Session` object.
session = werkzeug.LocalProxy(lambda: Session.current)

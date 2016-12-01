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
:mod:`craftr.targetbuilder`
===========================

Provides the :class:`TargetBuilder` and :class:`Framework` classes.
"""

from craftr.core import build
from craftr.core.logging import logger
from craftr.core.session import session
from craftr.utils import argspec, pyutils
from nr.py.bytecode import get_assigned_name

import collections
import sys


def get_full_name(target_name, module=None):
  """
  Given a *target_name*, this function generates the fully qualified name of
  that target that includes the *module* name and version. If *module* is
  omitted, the currently executed module is used.
  """

  if module is None:
    if not session:
      raise RuntimeError('no session context')
    module = session.module
    if not module:
      raise RuntimeError('no current module')

  return '{}.{}'.format(module.ident, target_name)


def gtn(target_name=None, name_hint=NotImplemented):
  """
  This function is mandatory in combination with the :class:`TargetBuilder`
  class to ensure that the correct target name can be deduced. If the
  *target_name* parmaeter is specified, it is returned right away. Otherwise,
  if it is :const:`None`, :func:`get_assigned_name` will be used to retrieve
  the variable name of the expression of 2 frames above this call.

  To visualize the behaviour, imagine you are using a target generator function
  like this:

  .. code:: python

      objects = cxx_compile(
        srcs = glob(['src/*.cpp'])
      )

  The ``cxx_compile()`` function would use the :class:`TargetBuilder`
  similar to what is shown below.

  .. code:: python

      builder = TargetBuilder(inputs, frameworks, kwargs, name = gtn(name))

  And the :func:`gtn` function will use the frame that ``cxx_compile()`` was
  called from to retrieve the name of the variable "objects". In the case that
  an explicit target name is specified, it will gracefully return that name
  instead of figuring the name of the assigned variable.

  If *name_hint* is :const:`None` and no assigned name could be determined,
  no exception will be raised but also no alternative target name will
  be generated and :const:`None` will be returned. This is useful for wrapping
  existing target generator functions.
  """

  if not session:
    raise RuntimeError('no session context')
  module = session.module
  if not module:
    raise RuntimeError('no current module')

  if target_name is None:
    try:
      target_name = get_assigned_name(sys._getframe(2))
    except ValueError:
      if name_hint is NotImplemented:
        raise
  elif '-' in target_name:
    # TODO: We should find a better way to determine if the target is
    # TODO: already an absolute target name.
    return target_name

  full_name = None
  if target_name is None:
    if name_hint is None:
      return None

    index = 0
    while True:
      target_name = '{}_{:0>4}'.format(name_hint, index)
      full_name = get_full_name(target_name, module)
      if full_name not in session.graph.targets:
        break
      index += 1

  if full_name is None:
    full_name = get_full_name(target_name, module)

  return full_name


class TargetBuilder(object):
  """
  This is a helper class for target generators that does a lot of convenience
  handling such as creating a :class:`OptionMerge` from the build options
  specified with the *frameworks* argument or from the input
  :class:`Targets<build.Target>`.

  :param name: The name of the target. Derive this target name by using
    the :func:`gtn` function.
  :param option_kwargs: A dictionary of additional call-level options
    that have been passed to the target generator function. These will
    take top priority in the :class:`OptionMerge`.
  :param inputs: A list of input files or :class:`build.Target` objects
    from which the outputs will be used as input files and the build
    options will be included in the :class:`OptionMerge`.
  :param frameworks: A list of build :class:`Framework` objects that will be
    included in the :class:`OptionMerge`.
  :param outputs: A list of output filenames.
  :param implicit_deps: A list of filenames added as implicit dependencies.
  :param order_only_deps: A list of filenames added as order only dependencies.
  """

  def __init__(self, name, option_kwargs=None, frameworks=(), inputs=(),
      outputs=(), implicit_deps=(), order_only_deps=()):
    argspec.validate('name', name, {'type': str})
    argspec.validate('option_kwargs', option_kwargs,
        {'type': [None, dict, Framework]})
    argspec.validate('frameworks', frameworks,
        {'type': [list, tuple], 'items': {'type': Framework}})
    argspec.validate('inputs', inputs,
        {'type': [list, tuple, build.Target],
          'items': {'type': [str, build.Target]}})
    argspec.validate('outputs', outputs,
        {'type': [list, tuple], 'items': {'type': str}})
    argspec.validate('implicit_deps', implicit_deps,
        {'type': [list, tuple], 'items': {'type': str}})
    argspec.validate('order_only_deps', order_only_deps,
        {'type': [list, tuple], 'items': {'type': str}})

    self.frameworks = list(frameworks)
    if isinstance(inputs, build.Target):
      inputs = [inputs]

    # If we find any Target objects in the inputs, expand the outputs
    # and append the frameworks.
    if inputs is not None:
      self.inputs = []
      for input_ in (inputs or ()):
        if isinstance(input_, build.Target):
          pyutils.unique_extend(self.frameworks, input_.frameworks)
          self.inputs += input_.outputs
        else:
          self.inputs.append(input_)
    else:
      self.inputs = None

    if option_kwargs is None:
      option_kwargs = {}

    self.name = name
    self.option_kwargs = Framework(name, **option_kwargs)
    self.option_kwargs_defaults = Framework(name + "_defaults")
    self.options_merge = OptionMerge(self.option_kwargs,
        self.option_kwargs_defaults, *self.frameworks)
    assert self.option_kwargs in self.options_merge.frameworks
    self.outputs = list(outputs)
    self.implicit_deps = list(implicit_deps)
    self.order_only_deps = list(order_only_deps)
    self.metadata = {}
    self.used_option_keys = set()

  def get(self, key, default=None):
    self.used_option_keys.add(key)
    return self.options_merge.get(key, default)

  def get_list(self, key):
    self.used_option_keys.add(key)
    return self.options_merge.get_list(key)

  def add_local_framework(self, *args, **kwargs):
    fw = Framework(*args, **kwargs)
    self.options_merge.append(fw)

  def setdefault(self, key, value):
    self.option_kwargs_defaults[key] = value

  def build(self, commands, inputs=(), outputs=(), implicit_deps=(),
      order_only_deps=(), metadata=None, **kwargs):
    """
    Create a :class:`build.Target` from the information in the builder,
    add it to the build graph and return it.
    """

    unused_keys = set(self.option_kwargs.keys()) - self.used_option_keys
    if unused_keys:
      logger.warn('TargetBuilder: "{}" unhandled option keys'.format(self.name))
      with logger.indent():
        for key in unused_keys:
          logger.warn('[-] {}={!r}'.format(key, self.option_kwargs[key]))

    # TODO: We could make this a bit shorter..
    inputs = self.inputs + list(inputs or ())
    outputs = self.outputs + list(outputs or ())
    implicit_deps = self.implicit_deps + list(implicit_deps or ())
    order_only_deps = self.order_only_deps + list(order_only_deps or ())
    if metadata is None:
      metadata = self.metadata
    elif self.metadata:
      raise RuntimeError('metadata specified in constructor and build()')

    implicit_deps = list(implicit_deps)
    for item in self.get_list('implicit_deps'):
      if isinstance(item, build.Target):
        implicit_deps += item.outputs
      elif isinstance(item, str):
        implicit_deps.append(item)
      else:
        raise TypeError('expected Target or str in "implicit_deps", found {}'
            .format(type(item).__name__))

    target = build.Target(self.name, commands, inputs, outputs, implicit_deps,
        order_only_deps, metadata=metadata, frameworks=self.frameworks, **kwargs)
    session.graph.add_target(target)
    return target


class Framework(dict):
  """
  A framework is simply a dictionary with a name to identify it. Frameworks
  are used to represent build options.
  """

  def __init__(self, __name=None, **kwargs):
    super().__init__(**kwargs)
    self.name = gtn(__name)

  def __repr__(self):
    return '<Framework "{}": {}>'.format(self.name, super().__repr__())


class OptionMerge(object):
  """
  This class represents a virtual merge of :class:`Framework` objects. Keys
  in the first dictionaries passed to the constructor take precedence over the
  last.

  :param frameworks: One or more :class:`Framework` objects. Note that
    the constructor will expand and flatten the ``'frameworks'`` list.
  """

  def __init__(self, *frameworks):
    self.frameworks = []
    [self.append(x) for x in frameworks]

  def __getitem__(self, key):
    for options in self.frameworks:
      try:
        return options[key]
      except KeyError:
        pass  # intentional
    raise KeyError(key)

  def append(self, framework):
    def update(fw):
      if not isinstance(framework, Framework):
        raise TypeError('expected Framework, got {}'.format(type(fw).__name__))
      pyutils.unique_append(self.frameworks, fw, id_compare=True)
      [update(x) for x in fw.get('frameworks', [])]
    update(framework)

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  def get_list(self, key):
    """
    This function returns a concatenation of all list values saved under the
    specified *key* in all option dictionaries in this OptionMerge object.
    It gives an error if one option dictionary contains a non-sequence for
    *key*.
    """

    result = []
    for option in self.frameworks:
      value = option.get(key)
      if value is None:
        continue
      if not isinstance(value, collections.Sequence):
        raise ValueError('found "{}" for key "{}" which is a non-sequence'
            .format(tpye(value).__name__, key))
      result += value
    return result

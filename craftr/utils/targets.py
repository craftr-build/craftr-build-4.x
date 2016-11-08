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

from craftr.core.session import session
from nr.py.bytecode import get_assigned_name

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
      return get_assigned_name(sys._getframe(2))
    except ValueError:
      if name_hint is NotImplemented:
        raise

    if name_hint is None:
      return None

    index = 0
    while True:
      target_name = '{}_{:0>4}'.format(name_hint, index)
      full_name = get_full_name(target_name, module)
      if full_name not in session.graph.targets:
        break
      index += 1

  return get_full_name(target_name, module)

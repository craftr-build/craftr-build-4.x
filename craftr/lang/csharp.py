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
:mod:`craftr.lang.csharp`
=========================

Provides a high-level interface for compiling C# projects.
"""

from craftr import platform
from craftr.core.session import session
from craftr.defaults import buildlocal
from craftr.targetbuilder import gtn, TargetBuilder
from craftr.utils import path, shell

# Default to the Microsoft C# compiler on Windows, Mono on all other platforms.
if platform.name == 'win':
  CSC = 'csc'
  RUNPREFIX = ''
else:
  CSC = 'mcs'
  RUNPREFIX = 'mono'


class CsCompiler(object):
  """
  A compiler interface for C# programs.
  """

  def __init__(self, program=None, runprefix=None):
    program = program or session.options.get('csharp.csc', CSC)
    runprefix = runprefix or session.options.get('csharp.runprefix', RUNPREFIX)
    self.program = program
    self.runprefix = shell.split(runprefix)

  def compile(self, filename, sources, target='exe', defines=(),
      optimize=True, warn=None, warnaserror=False, appconfig=None, baseaddress=None,
      checked=False, debug=False, main=None, platform=None, unsafe=False,
      win32icon=None, win32manifest=None, win32res=None, additional_flags=(),
      no_add_suffix=False, name=None):

    builder = TargetBuilder(gtn(name, 'csharp'), inputs=sources)
    filename = buildlocal(filename)
    if target in ('appcontainerexe', 'exe', 'winexe'):
      if not no_add_suffix:
        filename = path.addsuffix(filename, '.exe')
    elif target == 'library':
      if not no_add_suffix:
        filename = path.addsuffix(filename, '.dll')
    elif target == 'winmdobj':
      if not no_add_suffix:
        filename = path.addsuffix(filename, '.winmdobj')
    elif target == 'module':
      if not no_add_suffix:
        filename = path.addsuffix(filename, '.netmodule')
    else:
      raise ValueError('invalid target: {0!r}'.format(target))
    if warn not in (None, 0, 1, 2, 3, 4):
      raise ValueError('invalid warn: {0!r}'.format(warn))
    if platform not in (None, 'anycpu', 'anycpu32bitpreferred', 'ARM', 'x64', 'x86', 'Itanium'):
      raise ValueError('invalid platform: {0!r}'.format(platform))

    command = [self.program, '/nologo', '/out:$out']
    command += ['/warn:{0}'.format(warn)] if warn is not None else []
    command += ['/warnaserror'] if warnaserror else []
    command += ['/target:{0}'.format(target)]
    command += ['/define:{0}'.format(x) for x in defines]
    command += ['/appconfig:{0}'.format(appconfig)] if appconfig else []
    command += ['/baseaddress:{0}'.format(baseaddress)] if baseaddress else []
    command += ['/checked'] if checked else []
    command += ['/main:{0}'.format(main)] if main else []
    command += ['/platform:{0}'.format(platform)] if platform else []
    command += ['/unsafe'] if unsafe else []
    if debug:
      command += ['/debug']
    elif optimize:
      command += ['/optimize']
    command += ['/win32icon:{0}'.format(win32icon)] if win32icon else []
    command += ['/win32manifest:{0}'.format(win32manifest)] if win32manifest else []
    command += ['/win32res:{0}'.format(win32res)] if win32res else []
    command += ['$in']


    t = builder.build([command], None, [filename])
    print(t)
    print(t.commands)
    print(t.inputs)
    print(t.outputs)
    return t
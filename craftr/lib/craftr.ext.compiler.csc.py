# -*- mode: python -*-
# Copyright (C) 2016  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

__all__ = ['CSCompiler']

from craftr import Target


class CSCompiler(object):
  ''' Class for compiling C-Sharp programs using Microsoft CSC. '''

  def __init__(self, program='csc'):
    super().__init__()
    self.program = program

  def compile(self, filename, sources, target='exe', defines=(),
      optimize=True, warn=None, warnaserror=False, appconfig=None, baseaddress=None,
      checked=False, debug=False, main=None, platform=None, unsafe=False,
      win32icon=None, win32manifest=None, win32res=None, additional_flags=()):

    filename = path.normpath(filename, module.project_name)
    if target in ('appcontainerexe', 'exe', 'winexe'):
      filename = path.addsuffix(filename, '.exe')
    elif target == 'library':
      filename = path.addsuffix(filename, '.dll')
    elif target == 'winmdobj':
      filename = path.addsuffix(filename, '.winmdobj')
    elif target == 'module':
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

    return Target(command, sources, [filename])

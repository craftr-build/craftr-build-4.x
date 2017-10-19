"""
This module provides information on the current platform.
"""

import platform
import sys

if sys.platform.startswith('win32'):
  name = 'win32'
elif sys.platform.startswith('darwin'):
  name = 'darwin'
elif sys.platform.startswith('linux'):
  name = 'linux'
else:
  raise EnvironmentError('Unsupported platform: {}'.format(sys.platform))


class Triplet:
  """
  Represents a target machine triplet for the current platform. The target
  triple has the general format <arch><sub>-<vendor>-<sys>-<abi>, where:

  ```
  <arch> x86, arm, thumb, mips, etc.

  <sub>  for example on ARM: v5, v6m, v7a, v7m, etc.

  <vendor>
          pc, apple, nvidia, ibm, etc.

  <sys>  none, linux, win32, darwin, cuda, etc.

  <abi>  eabi, gnu, android, macho, elf, msvc, etc.
  ```
  """

  ARCH = ['x86', 'x86_64', 'arm', 'thumb', 'mips']
  VENDOR = ['pc', 'apple', 'nvidia', 'ibm']
  SYS = ['none', 'linux', 'win32', 'darwin', 'cuda']
  ABI = ['eabi', 'gnu', 'android', 'macho', 'elf', 'msvc']

  @classmethod
  def parse(cls, s):
    parts = s.split('-')
    if not parts or len(parts) < 3 or len(parts) > 4:
      raise ValueError('invalid triplet: {!r}'.format(s))
    arch = next((x for x in cls.ARCH if parts[0].startswith(x)), None)
    if not arch:
      raise ValueError('unexpected architecture: {!r}'.format(parts[0]))
    sub = parts[0][len(arch):]
    if len(parts) < 4:
      parts.append(None)
    else:
      parts.append(None)
    return cls(arch, sub, parts[1], parts[2], parts[3])

  @classmethod
  def current(cls):
    # TODO
    arch = platform.machine().lower()
    if arch == 'amd64':
      arch = 'x86_64'
    elif arch in ('x86', 'x86_64'):
      pass
    else:
      raise EnvironmentError('Unsupported platform arch: {}'.format(arch))
    return cls(arch, '', 'pc', name, None)

  def __init__(self, arch, sub, vendor, sys, abi):
    if arch not in self.ARCH:
      raise ValueError('unexpected arch: {!r}'.format(arch))
    if vendor not in self.VENDOR:
      raise ValueError('unexpected vendor: {!r}'.format(vendor))
    if sys not in self.SYS:
      raise ValueError('unexpected sys: {!r}'.format(sys))
    if abi is not None and abi not in self.ABI:
      raise ValueError('unexpected abi: {!r}'.format(abi))
    self.arch = arch
    self.sub = sub or ''
    self.vendor = vendor
    self.sys = sys
    self.abi = abi

  def __str__(self):
    return '{}{}-{}-{}'.format(self.arch, self.sub, self.vendor, self.sys) \
      + ('-{}'.format(self.abi) if self.abi else '')

  def __repr__(self):
    return '<Triplet {!r}>'.format(str(self))

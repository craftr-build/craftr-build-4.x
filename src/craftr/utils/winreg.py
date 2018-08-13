# -*- coding: utf8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2018  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import collections
import winreg

from winreg import (
  KEY_ALL_ACCESS,
  KEY_WRITE,
  KEY_READ,
  KEY_EXECUTE,
  KEY_QUERY_VALUE,
  KEY_SET_VALUE,
  KEY_CREATE_SUB_KEY,
  KEY_ENUMERATE_SUB_KEYS,
  KEY_NOTIFY,
  KEY_CREATE_LINK,
  KEY_WOW64_64KEY,
  KEY_WOW64_32KEY,
  REG_BINARY,
  REG_DWORD,
  REG_DWORD_LITTLE_ENDIAN,
  REG_DWORD_BIG_ENDIAN,
  REG_EXPAND_SZ,
  REG_LINK,
  REG_MULTI_SZ,
  REG_NONE,
  REG_RESOURCE_LIST,
  REG_FULL_RESOURCE_DESCRIPTOR,
  REG_RESOURCE_REQUIREMENTS_LIST,
  REG_SZ
)

Value = collections.namedtuple('Value', 'name data type')


class Key:
  """
  Represents a windows registry key.
  """

  def __init__(self, path, key, sam=KEY_READ):
    self._path = path
    self._key = key
    self._sam = sam

  def __str__(self):
    return '<craftr/utils/winreg:Key {!r}>'.format(self.name)

  @property
  def path(self):
    return self._path

  @property
  def name(self):
    return self._path.rsplit('\\', 1)[1]

  @property
  def _winreg_key(self):
    if self._key is None:
      root_name, path = self._path.split('\\', 1)
      root = getattr(winreg, root_name)
      self._key = winreg.OpenKey(root, path, 0, self._sam)
    return self._key

  def save(self, file_name):
    winreg.SaveKey(self._winreg_key, file_name)

  def close(self):
    winreg.CloseKey(self._winreg_key)

  def keys(self, sam=None):
    if sam is None:
      sam = self._sam
    key = self._winreg_key
    i = 0
    while True:
      try:
        value = winreg.EnumKey(key, i)
      except WindowsError:
        break
      yield Key(self._path + '\\' + value, None, sam)
      i += 1

  def key(self, key_name, sam=None):
    if sam is None:
      sam = self._sam
    return Key(self._path + '\\' + key_name, winreg.OpenKey(self._winreg_key, key_name, 0, sam), sam)

  def create_key(self, key_name):
    return Key(winreg.OpenKey(self._winreg_key, key_name))

  def delete_key(self, key_name):
    winreg.DeleteKey(self._winreg_key, key_name)

  def values(self):
    key = self._winreg_key
    i = 0
    while True:
      try:
        value = winreg.EnumValue(key, i)
      except WindowsError:
        break
      yield Value(*value)
      i += 1

  def value(self, value_name=None):
    return Value(value_name, *winreg.QueryValueEx(self._winreg_key, value_name))

  def set_value(self, value_name, type, value):
    setter = winreg.SetValue if isinstance(value, str) else winreg.SetValueEx
    setter(self._winreg_key, value_name, 0, type, value)

  def delete_value(self, value_name):
    winreg.DeleteValue(self._winreg_key, value_name)

  def flush(self):
    winreg.FlushKey(self._winreg_key)


HKEY_CLASSES_ROOT = Key('HKEY_CLASSES_ROOT', winreg.HKEY_CLASSES_ROOT)
HKEY_CURRENT_USER = Key('HKEY_CURRENT_USER', winreg.HKEY_CURRENT_USER)
HKEY_LOCAL_MACHINE = Key('HKEY_LOCAL_MACHINE', winreg.HKEY_LOCAL_MACHINE)
HKEY_USERS = Key('HKEY_USERS', winreg.HKEY_USERS)
HKEY_PERFORMANCE_DATA = Key('HKEY_PERFORMANCE_DATA', winreg.HKEY_PERFORMANCE_DATA)
HKEY_CURRENT_CONFIG = Key('HKEY_CURRENT_CONFIG', winreg.HKEY_CURRENT_CONFIG)
HKEY_DYN_DATA = Key('HKEY_DYN_DATA', winreg.HKEY_DYN_DATA)

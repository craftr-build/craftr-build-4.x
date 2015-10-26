# Copyright (C) 2015 Niklas Rosenstein
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

import craftr.utils
import os
import sys
import unittest


def _(path):
  if os.name == 'nt':
    path = path.replace('/', '\\')
    if path.startswith('\\'):
      path = 'c:' + path
  return path


class PathTest(unittest.TestCase):

  def test_addprefix(self):
    from craftr.utils.path import addprefix
    self.assertEqual(addprefix(_('foo/bar/baz'), _('spam-')), _('foo/bar/spam-baz'))
    self.assertEqual(
      addprefix([
        _('foo/bar/baz'),
        _('foo/bar/ham/cheeck'),
        _('/gogodo')], _('egg_')),
      [
        _('foo/bar/egg_baz'),
        _('foo/bar/ham/egg_cheeck'),
        _('/egg_gogodo')])

  def test_addsuffix(self):
    from craftr.utils.path import addsuffix
    self.assertEqual(addsuffix(_('foo/bar/baz'), _('.eggs'), True), _('foo/bar/baz.eggs'))
    self.assertEqual(addsuffix(_('foo/bar/baz.spam'), _('.eggs'), True), _('foo/bar/baz.eggs'))
    self.assertEqual(addsuffix(_('foo/bar/baz.spam'), None, True), _('foo/bar/baz'))
    self.assertEqual(addsuffix(_('foo/bar/baz.spam'), _(''), True), _('foo/bar/baz'))
    self.assertEqual(
      addsuffix([
        _('foo/bar/baz'),
        _('foo/bar/baz.spam'),
        _('foo/bar/baz.baz')], _('.eggs'), True),
      [
        _('foo/bar/baz.eggs'),
        _('foo/bar/baz.eggs'),
        _('foo/bar/baz.eggs')])

    self.assertEqual(addsuffix(_('foo/bar/baz.spam'), _('eggs'), False), _('foo/bar/baz.spameggs'))
    self.assertEqual(addsuffix(_('foo/bar/baz.spam'), _('.eggs'), False), _('foo/bar/baz.spam.eggs'))
    self.assertEqual(
      addsuffix([
        _('foo/bar/baz'),
        _('foo/bar/baz.spam'),
        _('foo/bar/baz.baz')], _('eggs'), False),
      [
        _('foo/bar/bazeggs'),
        _('foo/bar/baz.spameggs'),
        _('foo/bar/baz.bazeggs')])

  def test_commonpath(self):
    from craftr.utils.path import commonpath
    self.assertEqual(commonpath([_('/foo/bar'), _('/foo/bar/baz')]), _('/foo/bar'))
    self.assertEqual(commonpath([_('foo/bar'), _('foo/bar/baz')]), _('foo/bar'))
    with self.assertRaises(ValueError):
      commonpath([_('/foo/bar'), _('foo/bar/baz')])

  def test_move(self):
    from craftr.utils.path import move
    base = _('foo/bar')
    new_base = _('eggs/ham')
    files = [
      _('foo/bar/main.c'),
      _('foo/bar/spam.c'),
      _('foo/bar/utils/eggs.c')]
    expected = [
      _('eggs/ham/main.c'),
      _('eggs/ham/spam.c'),
      _('eggs/ham/utils/eggs.c')]
    self.assertEqual(move(files, base, new_base), expected)


class ListsTest(unittest.TestCase):

  def test_autoexpand(self):
    from craftr.utils.lists import autoexpand as a
    self.assertEqual(a('spam'), ['spam'])
    self.assertEqual(a(['spam']), ['spam'])
    self.assertEqual(a(('spam',)), ['spam'])
    self.assertEqual(a(['spam', ['eggs', ('and', set(['trails'])), 'ham']]),
                      ['spam', 'eggs', 'and', 'trails', 'ham'])



class DisTest(unittest.TestCase):

  def test_get_assigned_name(self):
    from craftr.utils import get_assigned_name
    var = get_assigned_name(sys._getframe())
    self.assertEqual(var, 'var')
    obj = type('', (), {})()
    obj.bar = get_assigned_name(sys._getframe())
    self.assertEqual(obj.bar, 'obj.bar')
    with self.assertRaises(ValueError):
      (x, y) = get_assigned_name(sys._getframe())
    with self.assertRaises(ValueError):
      get_assigned_name(sys._getframe())

# Copyright (C) 2015  Niklas Rosenstein
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

import dis
from craftr import magic
from craftr.magic import get_assigned_name, get_frame
from unittest import TestCase


class TestMagic(TestCase):
  ''' Tests for the `craftr.magic` module. '''

  def test_opstackd_validity(self):
    ''' Test if all keys in `magic.opstackd` are valid opcodes. '''

    for key in magic.opstackd:
      self.assertTrue(key in dis.opname, key)

  def test_get_assigned_name(self):
    ''' Test `magic.get_assigned_name()` in various use cases. '''

    obj = type('', (), {})

    foo = get_assigned_name(get_frame())
    self.assertEqual("foo", foo)

    spam = [get_assigned_name(get_frame())] + ["bar"]
    self.assertEqual("spam", spam[0])

    obj.eggs = (lambda: get_assigned_name(get_frame(1)))()
    self.assertEqual("eggs", obj.eggs)

    with self.assertRaises(ValueError):
      get_assigned_name(get_frame())

    with self.assertRaises(ValueError):
      # get_assigned_name() branch must be first part of the expression.
      spam = [42] + [get_assigned_name(get_frame())] + ["bar"]
      self.assertEqual("spam", spam[0])

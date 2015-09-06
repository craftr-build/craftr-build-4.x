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

import craftr.runtime
import io
import os
import unittest
import tempfile

from craftr.runtime import Module

stdout = io.StringIO()
craftr.logging.get_stdout = craftr.logging.get_stderr = lambda: stdout


class ModuleBaseTest(unittest.TestCase):

  def _mktemp(self):
    return open(tempfile.mktemp('.craftr'), 'w')

  def setUp(self):
    self.session = craftr.runtime.Session()
    self.session.path = [tempfile.gettempdir()]

    with self._mktemp() as fp:
      self.valid_file = fp.name
      fp.write(
        '\n'
        '\n'
        '# Hello Foo Bar\n'
        '# As many comments as we would like\n'
        '# craftr_module(craftr.test_runtime.valid)\n'
        '# Bam in ya eggs\n'
        '\n')

    with self._mktemp() as fp:
      self.invalid_file_1 = fp.name
      fp.write(
        'import os\n'
        '# craftr_module(craftr.test_runtime.invalid)\n')

    with self._mktemp() as fp:
      self.invalid_file_2 = fp.name
      fp.write(
        '# craftr_modulee(invalid?identifier)\n')

  def tearDown(self):
    os.remove(self.valid_file)
    os.remove(self.invalid_file_1)
    os.remove(self.invalid_file_2)


class ModuleTest(ModuleBaseTest):

  def test_valid_identifer(self):
    self.assertEqual(
      Module(self.session, self.valid_file).read_identifier(),
      'craftr.test_runtime.valid')

  def test_invalid_identifier_1(self):
    with self.assertRaises(craftr.runtime.InvalidModule):
      Module(self.session, self.invalid_file_1).read_identifier()

  def test_invalid_identifier_2(self):
    with self.assertRaises(craftr.runtime.InvalidModule):
      Module(self.session, self.invalid_file_2).read_identifier()


class SessionTest(ModuleBaseTest):

  def test_load_valid_module(self):
    module = self.session.load_module('craftr.test_runtime.valid')

  def test_load_invalid_module_1(self):
    with self.assertRaises(craftr.runtime.NoSuchModule):
      self.session.load_module('craftr.test_runtime.invalid')

  def test_load_invalid_module_2(self):
    with self.assertRaises(ValueError):
      self.session.load_module('invalid?identifier')

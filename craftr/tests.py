# Copyright (C) 2015 Niklas Rosenstein
# All rights reserved.

import craftr.runtime
import os
import unittest


class IdentifierTest(unittest.TestCase):

  def test_identifier(self):
    assert craftr.runtime.validate_identifier('Sources')
    assert craftr.runtime.validate_identifier('obJects_and_32Fun')
    assert craftr.runtime.validate_identifier('compiler.cpp.Wall')
    assert not craftr.runtime.validate_identifier(' Sources')
    assert not craftr.runtime.validate_identifier('Objects:Bar')
    assert not craftr.runtime.validate_identifier('Cpp-Fun')
    assert not craftr.runtime.validate_identifier('.Bar.Foo')
    assert not craftr.runtime.validate_identifier('compiler.cpp.')


class SessionTest(unittest.TestCase):

  def test_session(self):
    session = craftr.runtime.Session()
    assert os.getcwd() in session.path


class ModuleTest(unittest.TestCase):

  def test_module(self):
    pass


if __name__ == '__main__':
  unittest.main()


from os import chdir
from os.path import join, dirname
from subprocess import call
from nose.tools import *

basedir = dirname(dirname(__file__))


def export_and_build(directory):
  chdir(join(basedir, directory))
  assert_equals(call('craftr export'.split()), 0)
  assert_equals(call('craftr build'.split()), 0)


def test_example_c():
  export_and_build('examples/examples.c')

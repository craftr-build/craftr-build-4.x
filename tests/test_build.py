
from nose.tools import *
from nr import path
import {BuildSet} from '@craftr/craftr-build/build'


def test_buildset_subst():
  build = BuildSet('test')
  build.files.add(['main.c', 'foo.c'], ['in'])
  build.files.add(['foo.c'], ['optional'])
  build.files.add(['main'], ['out'])
  build.files.add(['main.d'], ['out', 'optional', 'depfile'])
  build.vars['include'] = ['include', 'somelib/include']

  assert_equals(build.subst(['$out']), [path.canonical('main'), path.canonical('main.d')])
  assert_equals(build.subst(['${out}']), [path.canonical('main'), path.canonical('main.d')])
  assert_equals(build.subst(['$in']), [path.canonical('main.c'), path.canonical('foo.c')])
  assert_equals(build.subst(['${in}']), [path.canonical('main.c'), path.canonical('foo.c')])
  assert_equals(build.subst(['$nonsense']), [])
  assert_equals(build.subst(['$include']), ['include', 'somelib/include'])
  assert_equals(build.subst(['$optional']), [path.canonical('foo.c'), path.canonical('main.d')])
  assert_equals(build.subst(['${in,optional}']), [path.canonical('foo.c')])
  assert_equals(build.subst(['${in,!optional}']), [path.canonical('main.c')])
  assert_equals(build.subst(['${out,optional}']), [path.canonical('main.d')])
  assert_equals(build.subst(['${out,!optional}']), [path.canonical('main')])

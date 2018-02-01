
from nose.tools import *
from craftr.core import Module, TargetHandler


class CxxHandler(TargetHandler):
  def setup_target(self, target):
    target.define_property('cxx.files', 'StringList')
  def setup_dependency(self, dep):
    dep.define_property('cxx.link', 'Bool')


def test_target_handler_inheritance():
  mod1 = Module('a', '1.0.0', '.')
  mod1.register_target_handler(CxxHandler())
  mod2 = Module('b', '1.0.0', '.')
  target = mod2.add_target('main')
  dep = target.add_dependency(mod1)

  assert_in('cxx', list(dep.scopes()))
  assert_in('link', list(x.name for x in dep.properties('cxx')))

  assert_in('cxx', list(target.scopes()))
  assert_in('files', list(x.name for x in target.properties('cxx')))


def test_transitive_exported_properties():
  mod1 = Module('a', '1.0.0', '.')
  mod1.register_target_handler(CxxHandler())
  mod2 = Module('b', '1.0.0', '.')
  mod3 = Module('c', '1.0.0', '.')

  t1 = mod1.add_target('t1')
  t1.add_dependency(mod1)
  t1['cxx'].files = ['a']

  t2 = mod2.add_target('t2', export=True)
  t2.add_dependency(mod1)
  t2.add_dependency(t1)
  t2['cxx'].__exported__.files = ['b']

  t3 = mod3.add_target('t3')
  t3.add_dependency(mod1)
  t3.add_dependency(t2)
  t3['cxx'].files = ['c']

  dep_targets = []
  for dep in t3.transitive_dependencies():
    dep_targets += dep.targets()
  assert_equals(dep_targets, [t2])

  assert_equals(t3.get_property('cxx.files'), ['c', 'b'])

  # Exporting t1 will cause t3 inherit the target's exported properties
  # through its depdency on mod1. Note the order of the output.
  t1._export = True
  assert_equals(t3.get_property('cxx.files'), ['c', 'b'])
  t1['cxx'].__exported__.files = t1['cxx'].files
  assert_equals(t3.get_property('cxx.files'), ['c', 'a', 'b'])
  t3._dependencies.reverse()
  assert_equals(t3.get_property('cxx.files'), ['c', 'b', 'a'])
  # Undo
  t1._export = False
  t3._dependencies.reverse()

  # Exporting the dependency of t2 to t1 will cause t3 to inherit t1.
  t2._dependencies[-1]._export = True
  assert_equals(t3.get_property('cxx.files'), ['c', 'b', 'a'])
  # Undo
  t2._dependencies[-1]._export = False
  t1['cxx'].__exported__.files = None

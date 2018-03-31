
from nose.tools import *
import {Context, Module, TargetHandler} from '@craftr/craftr-build/core'
import {Bool, StringList} from '@craftr/craftr-build/proplib'


class CxxHandler(TargetHandler):
  def init(self, context):
    context.target_properties.add('cxx.files', StringList)
    context.dependency_properties.add('cxx.link', Bool)


def test_target_handler_inheritance():
  ctx = Context()
  ctx.register_handler(CxxHandler())
  mod1 = Module(ctx, 'a', '1.0.0', '.')
  mod2 = Module(ctx, 'b', '1.0.0', '.')
  target = mod2.add_target('main')
  dep = target.add_dependency(mod1.public_targets())

  assert_equals(target.props['cxx.files'], [])
  assert_equals(dep.props['cxx.link'], False)


def test_transitive_exported_properties():
  ctx = Context()
  ctx.register_handler(CxxHandler())
  mod1 = Module(ctx, 'a', '1.0.0', '.')
  mod2 = Module(ctx, 'b', '1.0.0', '.')
  mod3 = Module(ctx, 'c', '1.0.0', '.')

  # t2 <- t1
  # t3 <- t2

  t1 = mod1.add_target('t1')
  t1.props['cxx.files'] = ['a']

  t2 = mod2.add_target('t2', public=True)
  t2.exported_props['cxx.files'] = ['b']
  t2.add_dependency([t1])

  t3 = mod3.add_target('t3')
  t3.props['cxx.files'] = ['c']
  t3.add_dependency(mod1.public_targets())
  t3.add_dependency([t2])

  dep_targets = []
  for dep in t3.transitive_dependencies():
    dep_targets += dep.sources
  assert_equals(dep_targets, [t2])

  assert_equals(t3.get_prop('cxx.files', True), ['c', 'b'])

  # Exporting t1 will cause t3 inherit the target's exported properties
  # through its depdency on mod1. Note the order of the output.
  t1.public = True
  assert_equals(t3.get_prop('cxx.files', True), ['c', 'b'])
  t1.exported_props['cxx.files'] = t1.get_prop('cxx.files')
  assert_equals(t3.get_prop('cxx.files', True), ['c', 'b'])
  t2.dependencies[0].public = True
  assert_equals(t3.get_prop('cxx.files', True), ['c', 'b', 'a'])

  t1.public = False
  t2.dependencies[0].public = False


import {Target, Behaviour} from 'craftr/target'
from nose.tools import *


def test_target_deps():
  a = Target('craftr', 'a', None)
  b = Target('craftr', 'b', None)
  c = Target('craftr', 'c', None)
  d = Target('craftr', 'd', None)
  e = Target('@another/namespace', 'e', None)
  f = Target('spam', 'f', None)

  c.parent = a
  assert c in a.children

  b.children.add(d)
  assert d.parent is b

  assert_equals(a.identifier(), '//craftr:a')
  assert_equals(b.identifier(), '//craftr:b')
  assert_equals(c.identifier(), '//craftr:a/c')
  assert_equals(d.identifier(), '//craftr:b/d')
  assert_equals(e.identifier(), '//@another/namespace:e')

  a.public_deps.add(e)
  b.private_deps.add(e)
  f.public_deps.add(a)
  f.public_deps.add(b)

  assert_equals(list(a.deps(children=False)), [e])
  assert_equals(list(a.deps()), [e])
  assert_equals(list(a.dependents()), [f])

  assert_equals(list(b.deps(children=False)), [e])
  assert_equals(list(b.deps()), [e])
  assert_equals(list(b.dependents()), [f])

  assert_equals(list(c.deps(children=False)), [])
  assert_equals(list(c.deps()), [])
  assert_equals(list(c.dependents()), [])
  assert_equals(list(c.dependents(transitive=True)), [f])

  assert_equals(list(d.deps(children=False)), [])
  assert_equals(list(d.deps()), [])
  assert_equals(list(d.dependents()), [])
  assert_equals(list(d.dependents(transitive=True)), [f])

  assert_equals(list(e.deps(children=False)), [])
  assert_equals(list(e.deps()), [])
  assert_equals(list(e.dependents()), [a, b])

  assert_equals(list(f.deps(children=False)), [a, b])
  assert_equals(list(f.deps()), [a, b, c, d])
  assert_equals(list(f.dependents()), [])


def test_target_behaviour():
  class MyBehaviour(Behaviour):
    def init(self, name):
      self.name = name
    def translate(self):
      self.target.add_action('hello', [['echo', 'Hello,', self.name]])
      self.target.add_action('bye', [['echo', 'Bye,', self.name]])

  t = Target('ham', 'spam', MyBehaviour)
  t.impl.init(name='John')
  t.impl.translate()

  assert_equals(len(list(t.actions())), 2)
  assert_equals(t.action('hello').deps, [])
  assert_equals(t.action('bye').deps, [t.action('hello')])
  assert_equals(list(t.actions(outputs=True)), [t.action('bye')])

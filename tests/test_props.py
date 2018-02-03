
from nose.tools import *
from craftr.props import *

def test_bool_strict():
  pt = Bool(strict=True)
  assert_equal(pt.coerce('a', True), True)
  assert_equal(pt.coerce('b', False), False)
  with assert_raises(TypeError): pt.coerce('c', 0)
  with assert_raises(TypeError): pt.coerce('d', 42)
  with assert_raises(TypeError): pt.coerce('e', [])
  with assert_raises(TypeError): pt.coerce('f', ['foobar'])
  with assert_raises(TypeError): pt.coerce('g', None)

def test_bool_nonstrict():
  pt = Bool(strict=False)
  assert_equal(pt.coerce('a', True), True)
  assert_equal(pt.coerce('a', False), False)
  assert_equal(pt.coerce('a', []), False)
  assert_equal(pt.coerce('a', None), False)
  assert_equal(pt.coerce('a', {}), False)
  assert_equal(pt.coerce('a', ['foobar']), True)
  assert_equal(pt.coerce('a', 0), False)
  assert_equal(pt.coerce('a', 42), True)

def test_integer_nonstrict():
  pt = Integer(strict=True)
  assert_equal(pt.coerce('x', 1), 1)
  assert_equal(pt.coerce('x', '42'), 42)
  with assert_raises(TypeError): pt.coerce('x', False)
  with assert_raises(TypeError): pt.coerce('x', True)
  with assert_raises(TypeError): pt.coerce('x', 'bam')

def test_integer_nonstrict():
  pt = Integer(strict=False)
  assert_equal(pt.coerce('x', 1), 1)
  assert_equal(pt.coerce('x', '42'), 42)
  assert_equal(pt.coerce('x', False), 0)
  assert_equal(pt.coerce('x', True), 1)
  with assert_raises(TypeError): pt.coerce('x', 'bam')

def test_list_any():
  pt = List()
  assert_equal(pt.coerce('a', []), [])
  assert_equal(pt.coerce('b', ('foobar', 42)), ['foobar', 42])
  with assert_raises(TypeError): pt.coerce('c', {})
  with assert_raises(TypeError): pt.coerce('d', None)
  with assert_raises(TypeError): pt.coerce('e', 1)

def test_list_int():
  pt = List(Integer())
  assert_equal(pt.coerce('a', []), [])
  assert_equal(pt.coerce('b', ()), [])
  assert_equal(pt.coerce('c', [42]), [42])
  assert_equal(pt.coerce('d', ['42']), [42])
  with assert_raises(TypeError): pt.coerce('e', ['foobar'])

def test_dict_any():
  import collections
  pt = Dict()
  assert_equal(pt.coerce('a', {'a': 'b'}), {'a': 'b'})
  assert_equal(pt.coerce('c', collections.OrderedDict()), {})
  with assert_raises(TypeError): pt.coerce('c', [])
  with assert_raises(TypeError): pt.coerce('d', 99)

def test_dict_string_int():
  import collections
  pt = Dict(String(), Integer())
  assert_equal(pt.coerce('a', {'foo': '99', 'bar': 2}), {'foo': 99, 'bar': 2})
  with assert_raises(TypeError): pt.coerce('b', {42: 2})

def test_propset():
  propset = PropertySet()
  scope = propset.add('scope')
  scope.add('opt1', Integer(), None, optional=True)
  scope.add('opt2', Integer(), 9, optional=True)
  with assert_raises(ValueError):  # Non-optional property requires default values.
    scope.add('req', Integer(), optional=False)
  scope.add('req', Integer(), 42, optional=False)
  with assert_raises(ValueError):  # Property already defined.
    scope.add('req', Integer())

  vals = Properties(propset)
  assert_equal(vals['scope.opt1'], None)
  assert_equal(vals['scope.opt2'], 9)
  assert_equal(vals['scope.req'], 42)

  vals['scope.opt1'] = None
  assert_equal(vals['scope.opt1'], None)
  vals['scope.opt1'] = 99
  assert_equal(vals['scope.opt1'], 99)
  vals['scope.opt1'] = None
  assert_equal(vals['scope.opt1'], None)

  with assert_raises(TypeError):
    vals['scope.opt1'] = 'foo'
  assert_equal(vals['scope.opt1'], None)

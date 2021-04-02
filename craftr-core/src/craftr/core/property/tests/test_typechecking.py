
import typing as t
import pytest
from craftr.core.property.typechecking import check_type, mutate_values, TypeCheckingError, TypeCheckingContext, MutableVisitContext


def test_check_type_list():
  check_type([], TypeCheckingContext(t.List))
  check_type([], TypeCheckingContext(list))
  check_type([1], TypeCheckingContext(t.List))
  check_type([1], TypeCheckingContext(t.List[int]))

  with pytest.raises(TypeCheckingError) as excinfo:
    check_type([1], TypeCheckingContext(t.List[str]))
  assert str(excinfo.value) == "at $.0: found int but expected str"


def test_check_type_dict():
  check_type({}, TypeCheckingContext(t.Dict))
  check_type({}, TypeCheckingContext(dict))
  check_type({'foo': 42}, TypeCheckingContext(t.Dict))
  check_type({'foo': 42}, TypeCheckingContext(t.Dict[str, int]))

  with pytest.raises(TypeCheckingError) as excinfo:
    check_type({'foo': 42}, TypeCheckingContext(t.Dict[int, int]))
  assert str(excinfo.value) == "at $.Key('foo'): found str but expected int"

  with pytest.raises(TypeCheckingError) as excinfo:
    check_type({'foo': 42}, TypeCheckingContext(t.Dict[str, str]))
  assert str(excinfo.value) == "at $.'foo': found int but expected str"

  with pytest.raises(TypeCheckingError) as excinfo:
    check_type({'foo': [0, 'bar']}, TypeCheckingContext(t.Dict[str, t.List[int]]))
  assert str(excinfo.value) == "at $.'foo'.1: found str but expected int"


def test_mutate_values_list():
  str_mutator = lambda v, t, c: str(v)
  value = [42, 1, 0]
  assert mutate_values(value, MutableVisitContext(t.List[int], str_mutator)) == ['42', '1', '0']
  assert mutate_values(value, MutableVisitContext(t.List, str_mutator)) == ['42', '1', '0']

  # mutate_values() only derives the value structure from the type hint, but does not
  # actually assert the individual item types.
  assert mutate_values(value, MutableVisitContext(t.List[str], str_mutator)) == ['42', '1', '0']

  # mutate_values() does not raise an exception if an unexpected type is encountered.
  assert mutate_values('foo', MutableVisitContext(t.List[int], int)) == 'foo'


def test_mutate_values_dict():
  str_mutator = lambda v, t, c: str(v)
  value = {1: 2, 3: 4}
  assert mutate_values(value, MutableVisitContext(t.Dict[int, int], str_mutator)) == {1: '2', 3: '4'}

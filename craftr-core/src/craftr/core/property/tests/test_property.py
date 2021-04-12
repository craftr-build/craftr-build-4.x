
import enum
import typing as t
from pathlib import Path
import pytest
from craftr.core.property.property import Box, Property, HavingProperties
from craftr.core.property.typechecking import TypeCheckingError


def test_having_properties_constructor():

  my_annotation = object()

  class MyClass(HavingProperties):
    a: Property[int]
    b: t.Annotated[Property[str], my_annotation]

  assert MyClass().get_properties().keys() == set(['a', 'b'])
  assert my_annotation in MyClass().b.annotations

  obj = MyClass()
  obj.a = 42
  obj.b = 'foo'

  assert obj.a.get() == 42
  assert obj.b.get() == 'foo'


def test_property_type_checking():

  class MyClass(HavingProperties):
    a: Property[int]
    b: Property[t.List[str]]

  obj = MyClass()

  with pytest.raises(TypeCheckingError) as excinfo:
    obj.a = 'foo'
  assert str(excinfo.value) == "while setting property MyClass.a: at $: found str but expected int"

  obj.a = Box('foo')
  with pytest.raises(TypeCheckingError) as excinfo:
    obj.a.get()
  assert str(excinfo.value) == "while getting property MyClass.a: at $: found str but expected int"


def test_property_annotation_in_value_hint():

  class MyClass(HavingProperties):
    a: t.Annotated[Property[int], 42]
    b: Property[t.Annotated[int, 42]]
    c: t.Annotated[Property[t.Annotated[int, 42]], 90]

  obj = MyClass()

  assert obj.get_properties()['a'].value_type == int
  assert obj.get_properties()['a'].annotations == [42]

  assert obj.get_properties()['b'].value_type == int
  assert obj.get_properties()['b'].annotations == [42]

  assert obj.get_properties()['c'].value_type == int
  assert obj.get_properties()['c'].annotations == [42, 90]


def test_property_operators():
  # Test concatenation if the property value is populated.
  prop1 = Property(t.List[str], [], 'prop1', None)
  prop1.set(['hello'])
  assert (prop1 + ['world']).get() == ['hello', 'world']

  prop1 = Property(str, [], 'prop1', None)
  prop1.set('hello')
  assert (prop1 + ' world').get() == 'hello world'

  # Concatenating an un-set property will fall back to an empty default.
  prop1 = Property(t.List[str], [], 'prop1', None)
  assert (prop1 + ['value']).get() == ['value']

  prop1 = Property(str, [], 'prop1', None)
  assert (prop1 + 'value').get() == 'value'


def test_property_nesting_1():
  prop1 = Property(t.List[str], [], 'prop1', None)
  prop2 = Property(str, [], 'prop2', None)
  prop1.set(['hello', prop2])
  prop2.set('world')
  assert prop1.get() == ['hello', 'world']


def test_property_nesting_2():
  prop1 = Property(t.List[t.List[str]], [], 'prop1', None)
  prop2 = Property(str, [], 'prop2', None)
  prop1.set([['hello', prop2]])
  prop2.set('world')
  assert prop1.get() == [['hello', 'world']]


def test_property_enum_coercion():
  class MyEnum(enum.Enum):
    ABC = enum.auto()

  prop = Property(MyEnum, [], 'myprop', None)
  prop.set('abc')
  assert prop.get() == MyEnum.ABC

  prop = Property(t.List[MyEnum], [], 'myprop', None)
  prop.set(['abc'])
  assert prop.get() == [MyEnum.ABC]


def test_property_path_coercion():
  prop = Property(Path, [], 'pathprop', None)
  prop.set('hello/world.c')
  assert prop.get() == Path('hello/world.c')

  prop = Property(t.List[Path], [], 'pathlistprop', None)
  prop.set(['hello/world.c'])
  assert prop.get() == [Path('hello/world.c')]

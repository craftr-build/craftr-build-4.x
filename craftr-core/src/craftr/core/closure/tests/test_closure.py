
import pytest

from craftr.core.closure import closure


def test_closure_local_variable_read():

  local_var = 'this is local'

  @closure()
  def _closure_1(ctx):
    assert ctx['local_var'] == 'this is local'
    # NOTE(NiklasRosenstein): Setting local variable in a closure is not currently supported.
    with pytest.raises(RuntimeError) as excinfo:
      ctx['local_var'] = 'new local'
    assert str(excinfo.value) == 'setting outter local variable from Closure is not supported. Use the `nonlocal` keyword.'
    return 'i have run'

  assert _closure_1() == 'i have run'


def test_closure_local_variable_update():

  @closure()
  def _closure_1(ctx):
    return ctx['local_var']

  local_var = 'this is local'
  assert _closure_1() == 'this is local'

  local_var = 'new local'
  assert _closure_1() == 'new local'


def test_closure_delegate_read():

  class HelloSayer:
    def say(self):
      return 'hi!'

  @closure()
  def _closure_1(ctx):
    assert ctx['say']() == 'hi!'

  _closure_1.apply(HelloSayer())


def test_closure_delegate_write():

  class HelloSayer:
    annotated_but_unset: str
    def __init__(self):
      self.some_attr = 'foobar'
    def say(self):
      return 'hi!'

  @closure()
  def _closure_1(ctx):

    assert ctx['say']() == 'hi!'
    with pytest.raises(RuntimeError) as excinfo:
      ctx['say'] = lambda: 'hello'
    assert str(excinfo.value) == 'cannot set function/method'

    # Annotated attributes are understood as properties, but accessing one that has not been
    # set will of course raise an AttributeError.
    with pytest.raises(AttributeError) as excinfo:
      ctx['annotated_but_unset']
    assert str(excinfo.value) == "'HelloSayer' object has no attribute 'annotated_but_unset'"

    # After setting the attribute, reading it works.
    ctx['annotated_but_unset'] = 'value'
    assert ctx['annotated_but_unset'] == 'value'

    # Instance attributes work as well.
    assert ctx['some_attr'] == 'foobar'
    ctx['some_attr'] = 'baz'
    assert ctx['some_attr'] == 'baz'

  _closure_1.apply(HelloSayer())


def test_closure_nesting():

  class HelloSayer:
    def say(self):
      return 'hello'

  @closure()
  def _closure_1(ctx):
    say = 'foobar'
    another_var = 42
    assert ctx['say']() == 'hello'
    @closure(ctx)
    def _closure_2(ctx):
      assert ctx['say']() == 'hello'
      assert ctx['another_var'] == 42
      return 'i ran'
    return _closure_2()

  assert _closure_1.apply(HelloSayer()) == 'i ran'


import utils from 'craftr/utils'
from nose.tools import *

def test_stream_01():
  x = utils.stream.map(range(10), lambda x: x*2)
  assert isinstance(x, utils.stream)
  assert_equals(list(x), [x*2 for x in range(10)])

def test_stream_02():
  x = utils.stream(range(10)).map(lambda x: x*2)
  assert isinstance(x, utils.stream)
  assert_equals(list(x), [x*2 for x in range(10)])

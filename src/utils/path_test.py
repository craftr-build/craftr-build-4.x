
from nose.tools import *
import stat
import {chmod_repr, chmod_update} from './path'


def test_chmod():
  f0 = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IROTH | stat.S_IXOTH
  assert_equals(chmod_repr(f0), 'rwx---r-x')

  f1 = chmod_update(f0, '+rwu-x')
  assert_equals(chmod_repr(f1), 'rw-rw-rwx')

  f2 = chmod_update(f0, 'a-rg+rwx')
  assert_equals(chmod_repr(f2), '-wxrwx--x')

  f3 = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
  assert_equals(chmod_repr(f3), 'rwxrw-rw-')

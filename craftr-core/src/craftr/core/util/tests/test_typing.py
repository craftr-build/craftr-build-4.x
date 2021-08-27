
import typing as t
import typing_extensions as te

from craftr.core.util.typing import unpack_type_hint


def test_unpack_type_hint():
  from typing import T
  assert unpack_type_hint(t.Any) == (t.Any, [])
  assert unpack_type_hint(list) == (list, [])
  assert unpack_type_hint(t.List) == (list, [T])
  assert unpack_type_hint(t.List[str]) == (list, [str])
  assert unpack_type_hint(t.Dict[str, int]) == (dict, [str, int])
  assert unpack_type_hint(t.List[t.Dict[str, int]]) == (list, [t.Dict[str, int]])
  assert unpack_type_hint(te.Annotated[int, 42]) == (te.Annotated, [int, 42])

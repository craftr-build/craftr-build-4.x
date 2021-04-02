
import typing as t

from craftr.core.util.typing import unpack_type_hint


def test_unpack_type_hint():
  assert unpack_type_hint(t.Any) == (t.Any, [])
  assert unpack_type_hint(list) == (list, [])
  assert unpack_type_hint(t.List) == (list, [])
  assert unpack_type_hint(t.List[str]) == (list, [str])
  assert unpack_type_hint(t.Dict[str, int]) == (dict, [str, int])
  assert unpack_type_hint(t.List[t.Dict[str, int]]) == (list, [t.Dict[str, int]])
  assert unpack_type_hint(t.Annotated[int, 42]) == (t.Annotated, [int, 42])

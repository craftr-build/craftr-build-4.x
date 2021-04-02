
import typing as t

T = t.TypeVar('T')


def unique(seq: t.Sequence[T]) -> t.List[T]:
  result: t.List[T] = []
  for item in seq:
    if item not in result:
      result.append(item)
  return result

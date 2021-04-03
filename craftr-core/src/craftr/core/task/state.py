
import hashlib
import typing as t
from pathlib import Path

from craftr.core.types import File
from craftr.core.util.typing import unpack_type_hint

if t.TYPE_CHECKING:
  from .task import Task


class _IHasher(t.Protocol):
  def update(self, data: bytes) -> None:  # NOSONAR
    pass


def _hash_file(hasher: _IHasher, path: Path) -> None:
  with path.open('rb') as fp:
    while True:
      chunk = fp.read(8048)
      hasher.update(chunk)
      if not chunk:
        break


def calculate_task_hash(task: 'Task', hash_algo: str = 'sha1') -> str:  # NOSONAR
  """
  Calculates a hash for the task that represents the state of it's inputs (property values
  and input file contents). That hash is used to determine if the task is up to date with
  it's previous execution or if it needs to be executed.

  > Implementation detail: Expects that all important information of a property value is
  > included in it's #repr(), and that the #repr() is consistent.
  """

  from .task import Task

  hasher = hashlib.new(hash_algo)
  encoding = 'utf-8'

  for prop in sorted(task.get_properties().values(), key=lambda p: p.name):
    hasher.update(prop.name.encode(encoding))
    hasher.update(repr(prop.or_none()).encode(encoding))

    item_type = unpack_type_hint(prop.value_type)
    is_input_file_property = (
        Task.Input in prop.annotations and (prop.value_type == File or item_type == File) \
        or Task.InputFile in prop.annotations)

    if is_input_file_property:
      value = prop.or_else(None)
      if value is not None:
        files = t.cast(t.Sequence[File], value if item_type else [value])
        for path in map(Path, files):
          if path.is_file():
            _hash_file(hasher, path)

  return hasher.hexdigest()

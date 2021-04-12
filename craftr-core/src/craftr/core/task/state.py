
import hashlib
import typing as t
from pathlib import Path

from craftr.core.property import Property
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


def check_file_property(prop: Property) -> t.Tuple[bool, bool, bool]:
  from .task import Task
  item_type = unpack_type_hint(prop.value_type)[1]
  is_sequence = item_type is not None and prop.value_type != Path
  is_file_type = (prop.value_type == Path or (item_type and item_type[0] == Path))
  is_input_file_property = (
      Task.Input in prop.annotations and is_file_type
      or Task.InputFile in prop.annotations)
  is_output_file_property = (
      Task.Output in prop.annotations and is_file_type
      or Task.OutputFile in prop.annotations)
  return is_sequence, is_input_file_property, is_output_file_property


def unwrap_file_property(prop: Property) -> t.Tuple[bool, bool, t.List[Path]]:
  is_sequence, is_input_file_property, is_output_file_property = check_file_property(prop)
  if not is_input_file_property and not is_output_file_property:
    return False, False, []
  value = prop.or_else(None)
  if value is None:
    result = []
  else:
    result = list(value if is_sequence else [value])
  return is_input_file_property, is_output_file_property, result


def calculate_task_hash(task: 'Task', hash_algo: str = 'sha1') -> str:  # NOSONAR
  """
  Calculates a hash for the task that represents the state of it's inputs (property values
  and input file contents). That hash is used to determine if the task is up to date with
  it's previous execution or if it needs to be executed.

  > Implementation detail: Expects that all important information of a property value is
  > included in it's #repr(), and that the #repr() is consistent.
  """

  hasher = hashlib.new(hash_algo)
  encoding = 'utf-8'

  for prop in sorted(task.get_properties().values(), key=lambda p: p.name):
    hasher.update(prop.name.encode(encoding))
    hasher.update(repr(prop.or_none()).encode(encoding))

    is_input, _is_output, files = unwrap_file_property(prop)
    if is_input:
      for path in map(Path, files):
        if path.is_file():
          _hash_file(hasher, path)

  return hasher.hexdigest()

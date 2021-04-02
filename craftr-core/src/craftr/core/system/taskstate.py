
import hashlib
import typing as t

if t.TYPE_CHECKING:
  from craftr.core.system.task import Task


def calculate_task_hash(task: 'Task', hash_algo: str = 'sha1') -> str:
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

  # TODO(NiklasRosenstein): Check file contents if the property value type is #File and
  #   it is annotated as an input.

  return hasher.hexdigest()

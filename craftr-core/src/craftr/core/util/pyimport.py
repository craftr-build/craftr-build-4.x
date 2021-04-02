
import importlib
import typing as t


def load_class(qualname: str) -> t.Type:
  module_name, member_name = qualname.rpartition('.')[::2]
  try:
    return getattr(importlib.import_module(module_name), member_name)
  except (AttributeError, ModuleNotFoundError, ValueError):
    raise ModuleNotFoundError(f'unable to load class {qualname!r}')

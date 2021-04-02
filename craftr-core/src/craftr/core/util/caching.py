
# Something to move into nr.caching maybe.

import base64
import json
import os
import time
import typing as t
from nr.caching.api import KeyDoesNotExist, KeyValueStore, NamespaceStore


class JsonDirectoryStore(NamespaceStore):
  """
  A namespace store that maps one namespace to a JSON file.
  """

  def __init__(self, directory: str, create_dir: bool = False) -> None:
    self._directory = directory
    if create_dir:
      os.makedirs(directory, exist_ok=True)

  def namespace(self, namespace: str) -> KeyValueStore:
    return JsonFileStore(os.path.join(self._directory, namespace + '.json'))

  def expunge(self, namespace: t.Optional[str]) -> None:
    if namespace:
      self.namespace(namespace).expunge()
    else:
      try:
        names = os.listdir(self._directory)
      except (FileNotFoundError, NotADirectoryError):
        names = []
      for name in names:
        if name.endswith('.json'):
          self.namespace(name[:-5]).expunge()


class JsonFileStore(KeyValueStore):
  """
  A very simple key value store backed by a JSON file. Really doesn't do anything fancy. Writes
  the JSON on every update. Not supported in a threading or multiprocessing context.
  """

  def __init__(self, filename: str) -> None:
    self._filename = filename
    self._values: t.Optional[t.Dict[str, t.Dict]] = None

  def _get_values(self) -> t.Dict[str, t.Dict]:
    if self._values is None and os.path.isfile(self._filename):
      with open(self._filename) as fp:
        self._values = json.load(fp)
    elif self._values is None:
      self._values = {}
    return self._values

  def _save(self) -> None:
    with open(self._filename, 'w') as fp:
      json.dump(self._values, fp)

  def load(self, key: str) -> bytes:
    try:
      entry = self._get_values()[key]
    except KeyError:
      raise KeyDoesNotExist(key)
    if entry['exp'] is not None and entry['exp'] < time.time():
      del self._values[key]
      raise KeyDoesNotExist(key)
    return base64.b85decode(entry['val'].encode('ascii'))

  def store(self, key: str, value: bytes, expires_in: t.Optional[int] = None) -> None:
    exp = time.time() + expires_in if expires_in is not None else None
    self._get_values()[key] = {'val': base64.b85encode(value).decode('ascii'), 'exp': exp}
    self._save()

  def expunge(self) -> None:
    t = time.time()
    data = self._get_values()
    has_deleted = False
    for key in list(data):
      entry = data[key]
      if entry['exp'] is not None and entry['exp'] < t:
        del data[key]
        has_deleted = True
    if has_deleted:
      self._save()

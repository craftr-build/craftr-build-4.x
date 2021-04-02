
import typing as t
from pathlib import Path

#: A union type that represents a file or directory on the local filesystem.
File = t.Union[str, Path]

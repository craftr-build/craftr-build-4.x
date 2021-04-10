
import enum
import re
import typing as t
from dataclasses import dataclass


class Type(enum.Enum):
  Marker = enum.auto()
  Body = enum.auto()


@dataclass
class Section:
  type: Type
  value: str
  line: int


def parse_section_file(content: str, marker_regex: t.Optional[str] = None) -> t.Iterator[Section]:
  r"""
  Parses a file comprised of section markers and body content. Example:

  ```
  === The Marker Value ==
  Body here
  ====== Another Marker ==

  ```

  The above is parsed into

  ```
  [
      Section(type=Type.Marker, value='The Marker Value', line=0),
      Section(type=Type.Body, value='Body here', line=1),
      Section(type=Type.Marker, value='Another Marker', line=2),
      Section(type=Type.Body, value='\n', line=3),
  ]
  ```

  A marker line must be prefixed and suffixed by at least two equal signs.
  """

  if marker_regex is None:
    marker_regex = r'^==+\s*([\d\w ]+?)\s*==+\n?'
  expr = re.compile(marker_regex, re.M | re.S)

  offset = 0
  line = 0
  while offset < len(content):
    match = expr.search(content, offset)
    if match is None:
      yield Section(Type.Body, content[offset:], line)
      break

    body = content[offset:match.start()]
    stripped_body = body[:-1] if body.endswith('\n') and len(body) > 1 else body
    if stripped_body:
      yield Section(Type.Body, stripped_body, line)
    line += body.count('\n')

    yield Section(Type.Marker, match.group(1), line)
    offset = match.end()
    line += 1

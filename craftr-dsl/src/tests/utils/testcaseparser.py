
import re
import typing as t
from dataclasses import dataclass
from pathlib import Path
from .sectionfileparser import parse_section_file, Type


@dataclass
class CaseData:
  filename: str
  name: str
  input: str
  input_line: int
  expects: str
  expects_line: int
  expects_syntax_error: bool


def parse_testcase_file(content: str, filename: str) -> t.Iterator[CaseData]:
  """
  Parses a Craftr DSL parser test case file. Such a file must be of the following form:

  ```
  === TEST <test_name> ===
  <craftr_dsl_code>
  <...>
  === EXPECTS ===
  <generated_python_code>
  <...>
  === END ===
  ```

  Multiple such blocks may be contained in a single file.
  """

  it = parse_section_file(content)
  try:
    while True:
      section = next(it, None)
      if not section:
        break
      if section.type == Type.Body and section.value.isspace():
        continue
      test_section = section
      if test_section.type != Type.Marker or not (m := re.match(r'(DISABLED\s+)?TEST\s+(\w+)$', test_section.value)):
        raise ValueError(f'{filename}: expected TEST section at line {test_section.line}, got {test_section}')
      test_disabled = m.group(1)
      test_name = m.group(2)
      test_body = next(it)
      if test_body.type != Type.Body:
        raise ValueError(f'{filename}: expected TEST section body at line {test_body.line}')
      expects_section = next(it)
      if expects_section.type != Type.Marker or not (m := re.match(r'EXPECTS(\s+SYNTAX ERROR)?$', expects_section.value)):
        raise ValueError(f'{filename}: expected EXPECTS section at line {expects_section.line}, got {expects_section}')
      expects_syntax_error = m.group(1)
      expects_body = next(it)
      if expects_body.type != Type.Body:
        raise ValueError(f'{filename}: expected EXPECTS section body at line {test_body.line}')
      end_section = next(it)
      if end_section.type != Type.Marker or not (m := re.match(r'END$', end_section.value)):
        raise ValueError(f'{filename}: expected END section at line {end_section.line}, got {end_section}')
      if not test_disabled:
        yield CaseData(filename, test_name, test_body.value, test_body.line, expects_body.value, expects_body.line, bool(expects_syntax_error))
  except StopIteration:
    raise ValueError(f'{filename}: incomplete test case section')

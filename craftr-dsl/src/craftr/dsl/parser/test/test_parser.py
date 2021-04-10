
import re
import unittest
import typing as t
from functools import partial
from pathlib import Path

from craftr.dsl.parser import CraftrParser

import pytest

INPUT_MARK = r'=== TEST (\w+) ==='
OUTPUT_MARK = '=== EXPECTS ==='
END_MARK = '=== END ==='


def load_tests(path: Path) -> t.Dict[str, t.Callable]:
  content = path.read_text()
  tests: t.Dict[str, t.Callable] = {}

  def test_func(test_name: str, input: str, output: str):
    assert CraftrParser(input, str(path) + ' :: ' + test_name)._rewrite() == output

  for match in re.finditer(INPUT_MARK, content):
    test_name = match.group(1)
    output_idx = content.find(OUTPUT_MARK, match.end())
    end_idx = content.find(END_MARK, match.end())
    assert output_idx >= 0, f"no output mark ({OUTPUT_MARK}) found for test {test_name} in '{path}'"
    assert end_idx >= 0, f"no end mark ({END_MARK}) found for test {test_name} in '{path}'"

    input = content[match.end():output_idx]
    output = content[output_idx + len(OUTPUT_MARK):end_idx]

    test_func.__name__ = 'test_' + test_name
    tests['test_' + test_name] = partial(test_func, test_name, input, output)

  if not tests:
    raise ValueError(f"'{path}' contains not tests")
  return tests


test_files = {path: load_tests(path) for path in (Path(__file__).parent / 'cases').iterdir()}
test_cases = [(path, name) for path, tests in test_files.items() for name in tests]


@pytest.mark.parametrize('path,name', test_cases)
def test_parser(path, name):
  test_files[path][name]()

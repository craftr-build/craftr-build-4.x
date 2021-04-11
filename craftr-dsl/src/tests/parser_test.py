
import re
import typing as t
from functools import partial
from pathlib import Path

from craftr.dsl.rewrite import Rewriter, SyntaxError
from .utils.testcaseparser import CaseData, parse_testcase_file

import pytest


testcases_dir = Path(__file__).parent / 'parser_testcases'
test_cases = {path: {t.name: t for t in parse_testcase_file(path.read_text(), str(path))} for path in testcases_dir.iterdir()}
test_parameters = [(path, name) for path, tests in test_cases.items() for name in tests]


@pytest.mark.parametrize('path,name', test_parameters)
def test_parser(path, name):
  case_data: CaseData = test_cases[path][name]
  print(case_data.input)

  rewriter = Rewriter(case_data.input + '\n', str(path))

  if case_data.expects_syntax_error:
    with pytest.raises(SyntaxError) as excinfo:
      rewriter.rewrite()
    assert excinfo.value.get_text_hint() == case_data.expects
  else:
    assert rewriter.rewrite().code == case_data.expects + '\n'

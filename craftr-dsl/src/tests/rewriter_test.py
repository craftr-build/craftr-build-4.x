
from pathlib import Path
import pytest
from craftr.dsl.rewrite import Rewriter, SyntaxError
from .utils.testcaseparser import CaseData, cases_from


@cases_from(Path(__file__).parent / 'rewriter_testcases')
def test_parser(case_data: CaseData) -> None:
  print('='*30)
  print(case_data.input)
  print('='*30)
  print(case_data.expects)
  print('='*30)

  rewriter = Rewriter(case_data.input, case_data.filename, supports_local_def=False)
  if case_data.expects_syntax_error:
    with pytest.raises(SyntaxError) as excinfo:
      rewriter.rewrite()
    print(excinfo.value.get_text_hint())
    print('='*30)
    assert excinfo.value.get_text_hint() == case_data.expects
  else:
    result = rewriter.rewrite().code
    print(result)
    print('='*30)
    assert result == case_data.expects

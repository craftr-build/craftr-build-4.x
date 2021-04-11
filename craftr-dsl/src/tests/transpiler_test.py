
from pathlib import Path
from craftr.dsl.transpiler import transpile_to_source
from .utils.testcaseparser import CaseData, cases_from


@cases_from(Path(__file__).parent / 'transpiler_testcases')
def test_transpiler(case_data: CaseData) -> None:
  print('='*30)
  print(case_data.input)
  print('='*30)
  print(case_data.expects)
  print('='*30)

  output = transpile_to_source(case_data.input, case_data.filename).rstrip()
  print(output)

  assert output == case_data.expects.rstrip()

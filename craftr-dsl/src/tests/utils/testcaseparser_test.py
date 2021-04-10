
from textwrap import dedent
from .testcaseparser import CaseData, parse_testcase_file


def test_testcaseparser():
  content = dedent('''
    === TEST abc ===
    foo bar
    === EXPECTS ===
    baz
    === END ===
  ''')

  result = list(parse_testcase_file(content, '<string>'))

  assert result == [
    CaseData('<string>', 'abc', 'foo bar', 2, 'baz', 4, False)
  ]

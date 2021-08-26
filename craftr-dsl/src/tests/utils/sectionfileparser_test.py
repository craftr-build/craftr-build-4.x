
import re
from textwrap import dedent
from .sectionfileparser import parse_section_file, Section, Type


def test_sectionfileparser():
  example, result = re.findall(r'```(.*?)```', parse_section_file.__doc__ or '', re.M | re.S)
  parsed = list(parse_section_file(dedent(example).lstrip()))
  evaluated = eval(result.strip(), {'Section': Section, 'Type': Type})
  assert parsed == evaluated


import io
import textwrap
from nose.tools import *
from craftr.dsl import Parser

def test_dsl_parser():
  source = textwrap.dedent('''
    project "myproject" v1.5.3
    options:
      int optionA
      bool optionB = (OSNAME == 'windows')
      str optionC = OSARCH
    pool "link" 42
    target "lib":
      dependency "cpp"
      export cpp.includes = ['include']
    export target "kazing":
      export dependency "@lib"
      dependency "cpp"
      dependency "foobar":
        cpp.link = True
      cpp.srcs = glob(
          patterns = ['src/*.cpp'],
          excludes = ['src/main.cpp']
        )
      export cpp.defines = [
          'BUILD_STATIC'
        ]
      export:
        cpp.staticLibraries = ['z']
      eval:
        if OSNAME == 'windows':
          print("Shicey!")
    ''').strip()
  parser = Parser()
  project = parser.parse(source)

  fp = io.StringIO()
  project.render(fp, 0)

  assert_equal(fp.getvalue().strip().split('\n'), source.split('\n'))

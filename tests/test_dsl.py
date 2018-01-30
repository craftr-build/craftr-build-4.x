
import io
import textwrap
from nose.tools import *
from craftr import dsl


class Context(dsl.Context):

  def __init__(self):
    self.options = {}

  def get_option(self, module_name, option_name):
    return self.options[module_name + '.' + option_name]


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

  fp = io.StringIO()
  project = dsl.Parser().parse(source)
  project.render(fp, 0)

  assert_equal(fp.getvalue().strip().split('\n'), source.split('\n'))


def test_options():
  source = textwrap.dedent('''
    project "myproject"
    options:
      int input
    eval
      response['answer'] = input
  ''')
  project = dsl.Parser().parse(source)
  context = Context()
  context.options['myproject.input'] = 42
  response = {}

  ip = dsl.Interpreter(context, '<test_options>')
  module = ip.create_module(project)
  module.eval_namespace().response = response
  ip.eval_module(project, module)

  assert_equals(response['answer'], 42)

  del context.options['myproject.input']
  with assert_raises(dsl.MissingRequiredOptionError):
    dsl.Interpreter(context, '<test_options>')(project)

  context.options['myproject.input'] = 'foobar'
  with assert_raises(dsl.InvalidOptionError):
    dsl.Interpreter(context, '<test_options>')(project)


def test_options_default():
  source = textwrap.dedent('''
    project "myproject"
    eval import sys
    options:
      str input = (
          sys.executable * 3
        )
    eval
      response['answer'] = input
  ''')
  project = dsl.Parser().parse(source)
  context = Context()
  response = {}

  ip = dsl.Interpreter(context, '<test_options>')
  module = ip.create_module(project)
  module.eval_namespace().response = response
  ip.eval_module(project, module)

  import sys
  assert_equals(response['answer'], sys.executable*3)

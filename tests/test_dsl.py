
import io
import textwrap
from nose.tools import *
from craftr import dsl


class AssignedScopeDoesNotExist(Exception):
  pass


class AssignedPropertyDoesNoteExist(Exception):
  pass


class Context(dsl.Context):

  def __init__(self, strict=False):
    self.options = {}
    self.strict = strict

  def get_option(self, module_name, option_name):
    return self.options[module_name + '.' + option_name]

  def assigned_scope_does_not_exist(self, filename, loc, scope, propset):
    if self.strict:
      raise AssignedScopeDoesNotExist(filename, loc, scope, propset)

  def assigned_property_does_not_exist(self, filename, loc, prop_name, propset):
    if self.strict:
      raise AssignedPropertyDoesNoteExist(filename, loc, prop_name, propset)


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

  ip = dsl.Interpreter(context, '<test_options_default>')
  module = ip.create_module(project)
  module.eval_namespace().response = response
  ip.eval_module(project, module)

  import sys
  assert_equals(response['answer'], sys.executable*3)


def test_options_syntax_error():
  source = textwrap.dedent('''
    project "myproject"
    options:
      str input = 42 foo
  ''')
  project = dsl.Parser().parse(source)
  ip = dsl.Interpreter(Context(), '<test_options_syntax_error>')
  try:
    ip(project)
  except SyntaxError as exc:
    assert_equals(exc.filename, '<test_options_syntax_error>')
    assert_equals(exc.lineno, 4)
  else:
    assert False, 'SyntaxError not raised'


def test_pool():
  source = textwrap.dedent('''
    project "myproject"
    pool "link" 99
  ''')
  project = dsl.Parser().parse(source)
  module = dsl.Interpreter(Context(), '<test_pool>')(project)
  assert_equals(module.pool('link').depth, 99)


def test_module_global_assignment():
  source = textwrap.dedent('''
    project "myproject"
    foo.bar = "bazinga"
  ''')
  project = dsl.Parser().parse(source)
  ip = dsl.Interpreter(Context(strict=True), '<test_module_global_assignment>')
  try:
    module = ip(project)
  except AssignedScopeDoesNotExist as exc:
    assert_equals(exc.args[0], '<test_module_global_assignment>')
    assert_equals(exc.args[1].lineno, 3)
    assert_equals(exc.args[2], 'foo')
  else:
    assert False, 'AssignedScopeDoesNotExist not raised'

  module = ip.create_module(project)
  module.define_property('foo.exists', 'String')
  try:
    ip.eval_module(project, module)
  except AssignedPropertyDoesNoteExist as exc:
    assert_equals(exc.args[0], '<test_module_global_assignment>')
    assert_equals(exc.args[1].lineno, 3)
    assert_equals(exc.args[2], 'foo.bar')
  else:
    assert False, 'AssignedPropertyDoesNoteExist not raised'

  module = ip.create_module(project)
  module.define_property('foo.bar', 'Int')
  with assert_raises(dsl.InvalidAssignmentError):
    ip.eval_module(project, module)

  module = ip.create_module(project)
  module.define_property('foo.bar', 'String')
  ip.eval_module(project, module)
  assert_equals(module.get_property('foo.bar'), 'bazinga')

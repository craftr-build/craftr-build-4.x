
import io
import re
import textwrap
from nose.tools import *
from craftr import core, dsl


class AssignedScopeDoesNotExist(Exception):
  pass


class AssignedPropertyDoesNoteExist(Exception):
  pass


class Context(dsl.BaseDslContext):

  def __init__(self, strict=False):
    self.modules = {}
    self.options = {}
    self.strict = strict

  def get_option(self, module_name, option_name):
    return self.options[module_name + '.' + option_name]

  def get_module(self, module_name):
    if module_name in self.modules:
      return self.modules[module_name]
    raise dsl.ModuleNotFoundError(module_name)

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
      # This is a comment.
      int optionA
      bool optionB = (OSNAME == 'windows')
      str optionC = OSARCH
    # This is a comment.
    pool "link" 42
    target "lib":
      # This is a comment.
      # This is a comment.
      dependency "cpp"
      export cpp.includes = ['include']
    eval:
    # Here's an eval block with a newline in between. This originally
    # caused an "unexpected indent" error. Parser._parse_expression()
    # must take empty newlines into account.
      print('Hello')

      print('Bar')
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

  # Remove the comments, they will not be in the re-formatted output.
  source = re.sub('^\s*#.*$\n', '', source, 0, re.M)
  # Also remove multiple successive newlines.
  source = re.sub('\n+', '\n', source)
  assert_equals(fp.getvalue().strip().split('\n'), source.split('\n'))


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


def test_target():
  source = textwrap.dedent('''
    project "myproject"
    pool "link" 4
    target "lib":
      dependency "cxx"
      export:
        cxx.includes = ['lib/include']
    export target "main":
      dependency "cxx"
      dependency "@lib"
      dependency "somelib":
        cxx.link = False
      dependency "someotherlib"
      this.pool = "link"
      cxx.srcs = ['src/main.cpp']
      export cxx.includes = ['include']
  ''')

  context = Context(strict=True)

  class CxxHandler(core.TargetHandler):
    def setup_target(self, target):
      target.define_property('cxx.srcs', 'StringList')
      target.define_property('cxx.includes', 'StringList')
    def setup_dependency(self, dep):
      dep.define_property('cxx.link', 'Bool')

  cxx_handler = CxxHandler()
  cxx = core.Module('cxx', '1.0.0', '.')
  cxx.register_target_handler(cxx_handler)
  context.modules['cxx'] = cxx
  somelib = core.Module('somelib', '1.0.0', '.')
  t1 = somelib.add_target('lib', export=True)
  t1.add_dependency(cxx)
  t1['cxx'].includes = ['somelib/include']
  context.modules['somelib'] = somelib
  someotherlib = core.Module('someotherlib', '1.0.0', '.')
  context.modules['someotherlib'] = someotherlib

  project = dsl.Parser().parse(source)
  module = dsl.Interpreter(context, '<test_target>')(project)

  assert_equals(len(list(module.targets())), 2)
  target = next(module.targets())
  assert_equals(target.name(), 'lib')
  assert_equals(target.is_exported(), False)
  target = list(module.targets())[1]
  assert_equals(target.name(), 'main')
  assert_equals(target.is_exported(), True)
  assert_equals(target, module.target('main'))
  assert_equals(list(target.target_handlers()), [cxx_handler])
  assert_equals(target.get_property('this.pool'), 'link')
  assert_equals(target.get_property('cxx.srcs'), ['src/main.cpp'])
  assert_equals(target.get_property('cxx.includes'), ['include', 'lib/include', 'somelib/include'])
  assert_equals(len(list(target.dependencies())), 4)
  dep = next(target.dependencies())
  assert_equals(dep.module(), cxx)
  dep = list(target.dependencies())[1]
  assert_equals(dep.module(), module)
  assert_equals(dep.target(), next(module.targets()))
  dep = list(target.dependencies())[2]
  assert_equals(dep.module(), somelib)
  assert_equals(dep.get_property('cxx.link'), False)
  dep = list(target.dependencies())[3]
  assert_equals(dep.module(), someotherlib)
  assert_equals(dep.get_property('cxx.link'), None)
  assert_equals(dep.get_property('cxx.link', False), False)
  assert_equals(dep.get_property('cxx.link', True), True)


import core from '@craftr/craftr-build/core'
import dsl from '@craftr/craftr-build/dsl'
import {Bool, String, StringList} from '@craftr/craftr-build/proplib'

import io
import re
import textwrap
import unittest
from nose.tools import *

# TODO: Adapt these test cases for the way Craftr modules are loaded via
#       Node.py now -- we could use a pathlib.Path subclass that represents
#       an in-memory file.
raise unittest.SkipTest()


class AssignedPropertyDoesNoteExist(Exception):
  pass


class Context(dsl.Context):

  def __init__(self, strict=False):
    super().__init__('debug', '.')
    self.strict = strict
    if strict:
      self.module_properties.allow_any = False

  def load_module(self, module_name):
    if module_name in self.modules:
      return self.modules[module_name]
    raise dsl.ModuleNotFoundError(module_name)

  def report_property_does_not_exist(self, filename, loc, prop_name, propset):
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
      requires "cpp"
      export cpp.includes = ['include']
    eval:
      #! Here's an eval block with a newline in between. This originally
      #! caused an "unexpected indent" error. Parser._parse_expression()
      #! must take empty newlines into account.
      #! Note that the eval block is parsed as an expression and keeps
      #! keeps its comments.
      print('Hello')

      print('Bar')
    public target "kazing":
      export requires "@lib"
      requires "cpp"
      requires "foobar":
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

  # Remove comments that will not be kept.
  source = re.sub('^\s*#[^!].*\n', '', source, 0, re.M)

  assert_equals(fp.getvalue().strip().split('\n'), source.split('\n'))


def test_options():
  source = textwrap.dedent('''
    project "myproject"
    options:
      int input
    eval
      response['answer'] = options.input
  ''')
  project = dsl.Parser().parse(source)
  context = Context()
  context.options['myproject.input'] = 42
  response = {}

  ip = dsl.Interpreter(None, context, '<test_options>')
  module = ip.create_module(project)
  context.get_exec_vars(module)['response'] = response
  ip.eval_module(project, module)

  assert_equals(response['answer'], 42)

  del context.options['myproject.input']
  with assert_raises(dsl.MissingRequiredOptionError):
    dsl.Interpreter(None, context, '<test_options>')(project)

  context.options['myproject.input'] = 'foobar'
  with assert_raises(dsl.InvalidOptionError):
    dsl.Interpreter(None, context, '<test_options>')(project)


def test_options_default():
  source = textwrap.dedent('''
    project "myproject"
    eval import sys
    options:
      str input = (
          sys.executable * 3
        )
    options:
      bool foo = False
    eval
      response['answer'] = (options.input, options.foo)
  ''')
  project = dsl.Parser().parse(source)
  context = Context()
  response = {}

  ip = dsl.Interpreter(None, context, '<test_options_default>')
  module = ip.create_module(project)
  context.get_exec_vars(module)['response'] = response
  ip.eval_module(project, module)

  import sys
  assert_equals(response['answer'], (sys.executable*3, False))


def test_options_syntax_error():
  source = textwrap.dedent('''
    project "myproject"
    options:
      str input = 42 foo
  ''')
  project = dsl.Parser().parse(source)
  ip = dsl.Interpreter(None, Context(), '<test_options_syntax_error>')
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
  module = dsl.Interpreter(None, Context(), '<test_pool>')(project)
  assert_equals(module.pools['link'], 99)


def test_module_global_assignment():
  source = textwrap.dedent('''
    project "myproject"
    foo.bar = "bazinga"
  ''')
  project = dsl.Parser().parse(source)
  context = Context(strict=True)
  ip = dsl.Interpreter(None, context, '<test_module_global_assignment>')
  try:
    module = ip(project)
  except AssignedPropertyDoesNoteExist as exc:
    assert_equals(exc.args[0], '<test_module_global_assignment>')
    assert_equals(exc.args[1].lineno, 3)
    assert_equals(exc.args[2], 'foo.bar')
  else:
    assert False, 'AssignedPropertyDoesNoteExist not raised'

  module = ip.create_module(project)
  context.module_properties.add('foo.exists', String())
  try:
    ip.eval_module(project, module)
  except AssignedPropertyDoesNoteExist as exc:
    assert_equals(exc.args[0], '<test_module_global_assignment>')
    assert_equals(exc.args[1].lineno, 3)
    assert_equals(exc.args[2], 'foo.bar')
  else:
    assert False, 'AssignedPropertyDoesNoteExist not raised'

  module = ip.create_module(project)
  context.module_properties.add('foo.bar', Integer())
  with assert_raises(dsl.InvalidAssignmentError):
    ip.eval_module(project, module)

  module = ip.create_module(project)
  del context.module_properties['foo.bar']
  context.module_properties.add('foo.bar', String())
  ip.eval_module(project, module)
  assert_equals(module.props['foo.bar'], 'bazinga')


def test_target():
  source = textwrap.dedent('''
    project "myproject"
    pool "link" 4
    target "lib":
      requires "cxx"
      export:
        cxx.includes = ['lib/include']
    public target "main":
      requires "cxx"
      requires "@lib"
      requires "somelib":
        cxx.link = False
      requires "someotherlib"
      this.pool = "link"
      cxx.srcs = ['src/main.cpp']
      export cxx.includes = ['include']
    public target "another":
      requires "@main"
  ''')

  context = Context(strict=True)

  class CxxHandler(core.TargetHandler):
    def init(self, context):
      props = context.target_properties
      props.add('cxx.srcs', StringList)
      props.add('cxx.includes', StringList)
      props = context.dependency_properties
      props.add('cxx.link', Bool, True)

  cxx_handler = CxxHandler()
  cxx = core.Module(context, 'cxx', '1.0.0', '.')
  context.register_handler(cxx_handler)
  context.modules['cxx'] = cxx
  somelib = core.Module(context, 'somelib', '1.0.0', '.')
  t1 = somelib.add_target('lib', public=True)
  t1.add_dependency(cxx.public_targets(), public=False)
  t1.exported_props['cxx.includes'] = ['somelib/include']
  context.modules['somelib'] = somelib
  someotherlib = core.Module(context, 'someotherlib', '1.0.0', '.')
  context.modules['someotherlib'] = someotherlib

  project = dsl.Parser().parse(source)
  module = dsl.Interpreter(None, context, '<test_target>')(project)

  tlib = module.targets['lib']
  assert_equals(tlib.get_prop('cxx.includes'), ['lib/include'])
  assert_equals(tlib.props['cxx.includes'], [])
  assert_equals(tlib.exported_props['cxx.includes'], ['lib/include'])

  assert_equals(len(list(module.targets.values())), 3)
  target = next(iter(module.targets.values()))
  assert_equals(target.name, 'lib')
  assert_equals(target.public, False)

  target = list(module.targets.values())[1]
  print(target, target.get_prop('cxx.includes'))
  d = list(target.transitive_dependencies().attr('sources').concat())
  for t in d:
    print(t, t.get_prop('cxx.includes'))

  assert_equals(target.name, 'main')
  assert_equals(target.public, True)
  assert_equals(target, module.targets['main'])
  assert_equals(context.handlers, [cxx_handler])
  assert_equals(target.get_prop('this.pool'), 'link')
  assert_equals(target.get_prop('cxx.srcs'), ['src/main.cpp'])
  assert_equals(target.get_prop_join('cxx.includes'), ['include', 'lib/include', 'somelib/include'])
  assert_equals(len(target.dependencies), 4)

  dep = target.dependencies[0]
  assert_equals(dep.sources, [])
  dep = target.dependencies[1]
  assert_equals(dep.sources, [module.targets['lib']])
  dep = target.dependencies[2]
  assert_equals(dep.sources, [somelib.targets['lib']])
  assert_equals(dep.props['cxx.link'], False)  # Overwritten
  dep = target.dependencies[3]
  assert_equals(dep.props['cxx.link'], True)  # Default

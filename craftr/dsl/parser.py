# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
This module implements the parser for the Craftr DSL.
"""

from nr import strex

import collections
import contextlib
import os
import string
import textwrap
import toml
import types

import core from '../core'


@contextlib.contextmanager
def override_member(obj, member, value):
  try:
    old_value = getattr(obj, member)
    has_member = True
  except AttributeError:
    has_member = False
  setattr(obj, member, value)
  try:
    yield
  finally:
    if has_member:
      setattr(obj, member, old_value)
    else:
      delattr(obj, member)


class Node:
  """
  Represents a node in the Craftr DSL AST.
  """

  def __init__(self, loc):
    if not isinstance(loc, strex.Cursor):
      raise TypeError('expected strex.Cursor')
    self.loc = loc

  def __repr__(self):
    return '<{}@{}>'.format(type(self).__name__, self.loc)


class Project(Node):

  def __init__(self, loc, name, version):
    super().__init__(loc)
    self.name = name
    self.version = version
    self.children = []

  def render(self, fp, depth):
    fp.write('project "{}"'.format(self.name))
    if self.version:
      fp.write(' v{}'.format(self.version))
    fp.write('\n')
    for child in self.children:
      child.render(fp, depth)


class LinkModule(Node):

  def __init__(self, loc, path):
    super().__init__(loc)
    self.path = path

  def render(self, fp, depth):
    assert depth == 0
    fp.write('link "{}"'.format(self.name))


class Configure(Node):

  def __init__(self, loc, if_expr):
    self.loc = loc
    self.data = collections.OrderedDict()
    self.if_expr = if_expr

  def loads(self, source):
    data = toml.loads(source, _dict=collections.OrderedDict)
    for section, values in data.items():
      for key, value in values.items():
        self.data[section + ':' + key] = value

  def render(self, fp, depth):
    assert depth == 0
    fp.write('configure')
    if self.if_expr:
      fp.write(' if ' + self.if_expr)
    fp.write(':\n')
    for line in toml.dumps(self.data).split('\n'):
      fp.write('  ' + line)


class Options(Node):

  DATATYPES = set(['int', 'bool', 'str'])

  @staticmethod
  def adapt(type_name, value):
    if type_name == 'int':
      if isinstance(value, str):
        return int(value)
      elif isinstance(value, int):
        return value
    elif type_name == 'bool':
      if isinstance(value, str):
        value = value.lower().strip()
        if value in ('1', 'true', 'on', 'yes'):
          return True
        elif value in ('0', 'false', 'off', 'no'):
          return False
      elif isinstance(value, bool):
        return value
    elif type_name == 'str':
      if isinstance(value, str):
        return value
    raise TypeError('expected {}, got {}'.format(type_name, type(value).__name__))

  def __init__(self, loc):
    super().__init__(loc)
    self.options = collections.OrderedDict()

  def add(self, loc, key, type, default=None):
    self.options[key] = (type, default, loc)

  def render(self, fp, depth):
    fp.write('options:\n')
    for key, (type, value, loc) in self.options.items():
      fp.write('  {} {}'.format(type, key))
      if value:
        fp.write(' = ')
        Assignment.render_expression(fp, 2, value)
      else:
        fp.write('\n')


class Eval(Node):

  def __init__(self, loc, source, remainder, if_expr=None):
    super().__init__(loc)
    self.source = source.rstrip()
    self.remainder = remainder
    self.if_expr = if_expr
    assert not (remainder and if_expr)

  def render(self, fp, depth):
    if self.remainder:
      assert depth == 0
      fp.write('eval:>>\n')
      fp.write(self.source)
    elif '\n' in self.source:
      fp.write('  ' * depth + 'eval')
      if self.if_expr:
        fp.write(' if ')
        fp.write(self.if_expr)
      fp.write(':\n')
      for line in self.source.split('\n'):
        if line:
          fp.write('  ' * (depth+1))
          fp.write(line)
        fp.write('\n')
    else:
      fp.write('  ' * depth + 'eval ')
      fp.write(self.source)
      fp.write('\n')


class Pool(Node):

  def __init__(self, loc, name, depth):
    super().__init__(loc)
    self.name = name
    self.depth = depth

  def render(self, fp, depth):
    fp.write('pool "{}" {}\n'.format(self.name, self.depth))


class Target(Node):

  def __init__(self, loc, name, public, if_expr=None):
    super().__init__(loc)
    self.name = name
    self.public = public
    self.if_expr = if_expr
    self.children = []  # Requires, Assignment, Eval

  def render(self, fp, depth):
    if self.public:
      fp.write('public ')
    fp.write('target "{}"'.format(self.name))
    if self.if_expr:
      fp.write(' if ')
      fp.write(self.if_expr)
    fp.write(':\n')
    for child in self.children:
      child.render(fp, depth+1)


class Assignment(Node):

  def __init__(self, loc, scope, propname, expression, export):
    super().__init__(loc)
    self.scope = scope
    self.propname = propname
    self.expression = expression
    self.export = export

  def render(self, fp, depth):
    fp.write('  ' * depth)
    if self.export:
      fp.write('export ')
    fp.write('{} = '.format(self.scope + '.' + self.propname))
    self.render_expression(fp, depth+1, self.expression)

  @staticmethod
  def render_expression(fp, depth, expression):
    lines = expression.rstrip().split('\n')
    fp.write(lines[0])
    fp.write('\n')
    for line in lines[1:]:
      fp.write('  ' * depth)
      fp.write(line)
      fp.write('\n')


class Export(Node):

  def __init__(self, loc, if_expr=None):
    super().__init__(loc)
    self.assignments = []
    self.if_expr = if_expr

  def render(self, fp, depth):
    fp.write('  ' * depth + 'export')
    if self.if_expr:
      fp.write(' if ')
      fp.write(self.if_expr)
    fp.write(':\n')
    for assign in self.assignments:
      assign.render(fp, depth+1)


class Dependency(Node):

  def __init__(self, loc, name, export, assign_to=None, if_expr=None):
    super().__init__(loc)
    self.name = name
    self.export = export
    self.assign_to = assign_to
    self.if_expr = if_expr
    self.assignments = []

  def render(self, fp, depth):
    fp.write('  ' * depth)
    if self.export:
      fp.write('export ')
    fp.write('requires "{}"'.format(self.name))
    if self.assign_to:
      fp.write(' as {}'.format(self.assign_to))
    if self.if_expr:
      fp.write(' if ')
      fp.write(self.if_expr)
    fp.write(':\n' if self.assignments else '\n')
    for assign in self.assignments:
      assign.render(fp, depth+1)


class Parser:

  rules = [
    strex.Regex('comment', '#.*', skip=True),
    strex.Regex('string', '"([^"]*)"'),
    strex.Regex('string', "'([^']*)'"),
    strex.Regex('version', 'v(\d+\.\d+\.\d+)'),
    strex.Charset('number', string.digits),
    strex.Charset('name', string.ascii_letters + string.digits + '_'),
    strex.Keyword('=', '='),
    strex.Keyword(':', ':'),
    strex.Keyword('>>', '>>'),
    strex.Keyword('.', '.'),
    strex.Keyword('nl', '\n'),
    strex.Charset('ws', '\t ', skip=True),
  ]

  KEYWORDS = ['project', 'configure', 'options', 'eval', 'pool', 'link_module',
              'export', 'public', 'target', 'requires', 'import']

  def parse(self, source, filename='<input>'):
    lexer = strex.Lexer(strex.Scanner(source), self.rules)
    # TODO: Catch TokenizationError, UnexpectedTokenError
    try:
      return self._parse_project(lexer)
    except ParseError as e:
      e.filename = filename
      raise
    except strex.TokenizationError as e:
      raise ParseError(e.token.cursor, repr(e.token.value), filename)
    except strex.UnexpectedTokenError as e:
      raise ParseError(e.token.cursor, 'unexpected token "{}"'.format(e.token.type), filename)

  def _skip(self, lexer):
    while lexer.accept('nl'):
      pass

  def _parse_project(self, lexer):
    self._skip(lexer)
    token = lexer.next('name')
    if token.value != 'project':
      raise ParseError(token.cursor, 'expected keyword "project"')
    loc = token.cursor
    name = lexer.next('string').value.group(1)
    token = lexer.accept('version')
    version = token.value.group(1) if token else '1.0.0'
    lexer.next('nl', 'eof')
    project = Project(loc, name, version)
    self._skip(lexer)
    while lexer.token.type != 'eof':
      project.children.append(self._parse_stmt_or_block(lexer))
      self._skip(lexer)
    return project

  def _parse_stmt_or_block(self, lexer, keywords=None, parent_indent=None, export=False, public=False):
    if keywords is None:
      keywords = self.KEYWORDS
    token = lexer.next('name', 'eof')
    if token.type == 'eof':
      return None
    loc = token.cursor

    # This was not prefixed by "export".
    if not export and not public:
      if (parent_indent is None and loc.colno != 0):
        raise ParseError(loc, 'unexpected indent')
      if (parent_indent is not None and loc.colno <= parent_indent):
        # Needs to be parsed in a different context.
        lexer.scanner.restore(loc)
        return None
      parent_indent = loc.colno

    if 'export' in keywords and token.value == 'export' and not lexer.accept(':'):
      if export:
        raise ParseError(loc, 'unexpected keyword "export"')
      sub_keywords = []
      if 'configure' in keywords: sub_keywords.append('configure')
      if 'requires' in keywords: sub_keywords.append('requires')
      return self._parse_stmt_or_block(lexer, sub_keywords, parent_indent, export=True)
    if 'public' in keywords and token.value == 'public' and not lexer.accept(':'):
      sub_keywords = []
      if 'target' in keywords: sub_keywords.append('target')
      return self._parse_stmt_or_block(lexer, sub_keywords, parent_indent, public=True)

    if token.value == 'export' and lexer.token.type == ':':
      lexer.scanner.restore(lexer.token.cursor)

    if token.value in keywords:
      kwargs = {'parent_indent': parent_indent}
      if export: kwargs['export'] = export
      if public: kwargs['public'] = public
      return getattr(self, '_parse_' + token.value)(lexer, **kwargs)
    elif token.value in self.KEYWORDS:
      raise ParseError(loc, 'unexpected keyword "{}"'.format(token.value))

    return self._parse_assignment(lexer, parent_indent, export=export)

  def _parse_assignment(self, lexer, parent_indent, export=False):
    token = lexer.token
    loc = token.cursor
    scope = token.value
    lexer.next('.')
    propname = lexer.next('name').value
    lexer.next('=')
    value = self._parse_expression(lexer, parent_indent)
    lexer.next('nl', 'eof')
    return Assignment(loc, scope, propname, value, export)

  def _parse_expression(self, lexer, parent_indent):
    if lexer.scanner.colno == 0:
      first_line = None
    else:
      first_line = lexer.scanner.readline()
    sub_lines = []
    while True:
      loc = lexer.scanner.cursor
      match = lexer.scanner.match('[\t ]*')
      if lexer.scanner.char and lexer.scanner.char in '#\n':
        # Simply read in empty lines, but make sure we keep their
        # indentation as otherwise the dedentation doesn't work.
        indent = max(len(match.group(0)), parent_indent)
        sub_lines.append(' ' * indent + lexer.scanner.readline())
        continue
      if len(match.group(0)) <= parent_indent:
        lexer.scanner.restore(loc)
        break
      sub_lines.append(match.group(0) + lexer.scanner.readline())
    # Restore the last new-line, as it serves as statement delimiter.
    if (not sub_lines and first_line and first_line.endswith('\n')) or \
        (sub_lines and sub_lines[-1].endswith('\n')):
      lexer.scanner.seek(-1, 'cur')
    # Strip lines that are only comments/newlines.
    while sub_lines:
      line = sub_lines[-1].lstrip()
      if line.startswith('#') or line.startswith('\n') or not line:
        sub_lines.pop(-1)
      else:
        break
    result = textwrap.dedent(''.join(x for x in sub_lines))
    if first_line:
      result = first_line.strip() + '\n' + result
    return result

  def _parse_configure(self, lexer, parent_indent):
    loc = lexer.token.cursor
    if_expr = self._parse_block_if_expr(lexer, allow_non_block=False)
    lexer.next(':')
    block = Configure(loc, if_expr)
    block.loads(self._parse_expression(lexer, parent_indent))
    return block

  def _parse_options(self, lexer, parent_indent):
    options = Options(lexer.token.cursor)
    lexer.next(':')
    lexer.next('nl')
    while True:
      self._skip(lexer)
      token = lexer.next('name', 'eof')
      if token.type == 'eof' or token.cursor.colno <= parent_indent:
        lexer.scanner.restore(token.cursor)
        break  # Needs to be parsed in a different context
      loc = token.cursor
      dtype = token.value
      if dtype not in Options.DATATYPES:
        raise ParseError(token.cursor, 'expected ' + str(set(Options.DATATYPES)))
      token = lexer.next('name')
      if token.value in options.options:
        raise ParseError(token.cursor, 'duplicate option {!r}'.format(token.value))
      name = token.value
      token = lexer.accept('=')
      if token:
        value = self._parse_expression(lexer, loc.colno)
      else:
        value = None
      options.add(loc, name, dtype, value)
      lexer.next('nl', 'eof')
    if not options.options:
      raise ParseError(lexer.token.cursor, 'expected at least one indented statement')
    return options

  def _parse_eval(self, lexer, parent_indent):
    loc = lexer.token.cursor
    if_expr = self._parse_block_if_expr(lexer, allow_non_block=True)
    is_remainder = False

    if (if_expr and lexer.next(':')) or (not if_expr and lexer.accept(':')):
      if lexer.accept('>>'):
        is_remainder = True
      lexer.next('nl')
      loc.lineno += 1

    if is_remainder and parent_indent:
      raise ParseError(lexer.token.cursor, 'eval:>> block only on top-level')

    if is_remainder:
      lines = []
      while lexer.scanner:
        lines.append(lexer.scanner.readline())
      source = ''.join(lines)
    else:
      source = self._parse_expression(lexer, loc.colno)

    return Eval(loc, source, is_remainder, if_expr)

  def _parse_import(self, lexer, parent_indent):
    assert not parent_indent
    loc = lexer.token.cursor
    source = self._parse_expression(lexer, loc.colno)
    return Eval(loc, 'import ' + source, False)

  def _parse_pool(self, lexer, parent_indent):
    loc = lexer.token.cursor
    name = lexer.next('string').value.group(1)
    depth = int(lexer.next('number').value)
    lexer.next('nl', 'eof')
    return Pool(loc, name, depth)

  def _parse_target(self, lexer, parent_indent, public=False):
    loc = lexer.token.cursor
    name = lexer.next('string').value.group(1)
    if_expr = self._parse_block_if_expr(lexer)
    lexer.next(':')
    lexer.next('nl')
    subblocks = ['requires', 'eval', 'export']
    target = Target(loc, name, public, if_expr)
    while True:
      self._skip(lexer)
      child = self._parse_stmt_or_block(lexer, subblocks, parent_indent)
      if not child: break
      target.children.append(child)
    return target

  def _parse_requires(self, lexer, parent_indent, export=False):
    loc = lexer.token.cursor
    name = lexer.next('string').value.group(1)

    # Check if there's an "as <name>" portion that will assign the
    # modules' namespace to that variable in the target block.
    checkpoint = lexer.scanner.cursor
    token = lexer.accept('name')
    if token and token.value == 'as':
      assign_to = lexer.next('name').value
    else:
      lexer.scanner.restore(checkpoint)
      assign_to = None

    if_expr = self._parse_block_if_expr(lexer, allow_non_block=True)
    dep = Dependency(loc, name, export, assign_to, if_expr)
    if lexer.accept(':'):
      lexer.next('nl')
      while True:
        self._skip(lexer)
        child = self._parse_stmt_or_block(lexer, [], parent_indent)
        if not child: break
        assert isinstance(child, Assignment)
        dep.assignments.append(child)
    else:
      lexer.next('nl', 'eof')
    return dep

  def _parse_export(self, lexer, parent_indent):
    if_expr = self._parse_block_if_expr(lexer)
    if not if_expr:
      lexer.next(':')
    export = Export(lexer.token.cursor, if_expr)
    while True:
      self._skip(lexer)
      child = self._parse_stmt_or_block(lexer, ['requires'], parent_indent)
      if not child: break
      assert isinstance(child, (Assignment, Dependency))
      export.assignments.append(child)
    return export

  def _parse_link_module(self, lexer, parent_indent):
    loc = lexer.token.cursor
    path = lexer.next('string').value.group(1)
    lexer.next('nl', 'eof')
    return LinkModule(loc, path)

  def _parse_block_if_expr(self, lexer, allow_non_block=False):
    loc = lexer.token.cursor
    token = lexer.accept('name')
    if not token: return None
    if token.value == 'if':
      line = lexer.scanner.readline()
      result = line.partition('#')[0].rstrip()
      if result.endswith(':'):
        result = result[:-1]
        lexer.scanner.seek(len(result)-len(line), 'cur')
      elif line.endswith('\n'):
        lexer.scanner.seek(-1, 'cur')
      elif not allow_non_block:
        raise ParseError(loc, 'missing : at the end of conditional block')
      return result.lstrip()
    elif allow_non_block:
      lexer.scanner.restore(token.cursor)  # TODO: Restore previous token?
      return None
    else:
      raise ParseError(loc, 'expected "if" or ":", got {!r}'.format(token.value))


class ParseError(Exception):

  def __init__(self, loc, message, filename='<input>'):
    assert isinstance(loc, strex.Cursor)
    self.loc = loc
    self.message = message
    self.filename = filename

  def __str__(self):
    return '{}: line {}, col {}: {}'.format(self.filename,
      self.loc.lineno, self.loc.colno, self.message)

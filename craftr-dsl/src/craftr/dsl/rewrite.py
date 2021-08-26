
"""
Rewrite Craftr DSL code to pure Python code.
"""

import contextlib
import enum
import typing as t
from dataclasses import dataclass
from termcolor import colored

from nr.parsing.core import rules
from nr.parsing.core.scanner import Cursor
from nr.parsing.core.tokenizer import ProxyToken as _ProxyToken, RuleSet, Tokenizer


class Token(enum.Enum):
  Eof = enum.auto()
  Indent = enum.auto()
  Whitespace = enum.auto()
  Newline = enum.auto()
  Comment = enum.auto()
  Name = enum.auto()
  Literal = enum.auto()
  Control = enum.auto()


rule_set = RuleSet((Token.Eof, ''))
rule_set.rule(Token.Indent, rules.regex_extract(r'[\t ]*', at_line_start_only=True))
rule_set.rule(Token.Newline, rules.regex_extract(r'\n'))
rule_set.rule(Token.Whitespace, rules.regex_extract(r'\s+'))
rule_set.rule(Token.Comment, rules.regex_extract(r'#.*'))
rule_set.rule(Token.Control, rules.regex_extract(r'is|not'))
rule_set.rule(Token.Name, rules.regex_extract(r'[A-Za-z\_][A-Za-z0-9\_]*'))
rule_set.rule(Token.Literal, rules.regex_extract(r'[+\-]?(\d+)(\.\d*)?'))
rule_set.rule(Token.Literal, rules.string_literal())
rule_set.rule(Token.Control, rules.regex_extract(
  r'(\[|\]|\{|\}|\(|\)|<<|<|>>|>|\.|,|\->|\-|!|\+|\*\*|\*|//|/|->|==|<=|>=|<|>|=|:|&|\||^|%|@|;)'))


class ProxyToken(_ProxyToken):
  """
  Extension class that adds some useful utility methods to test the contents of the token.
  """

  def is_ignorable(self, newlines: bool = False) -> bool:
    if newlines and self.type == Token.Newline:
      return True
    return self.type in (Token.Indent, Token.Whitespace, Token.Comment)

  def is_control(self, charpool: t.Collection[str]) -> bool:
    return self.type == Token.Control and self.value in charpool


class ParseMode(enum.IntFlag):
  """ Flags that describe the current parse environment. """

  #: Nothing specific.
  DEFAULT = 0

  #: The currently parsed expression is grouped in parenthesis and may wrap over lines.
  GROUPED = 1

  #: The currently parsed expression is the outter parenthesis of a function call.
  FUNCTION_CALL = (1 << 1)

  #: The currently parsed expression is an argument to a function call.
  CALL_ARGS = (1 << 2)


@dataclass
class SyntaxError(Exception):
  """
  Specialized Craftr DSL syntax error (the internal SyntaxError class is weird).
  """

  message: str
  filename: str
  line: int
  column: int
  text: str

  def get_text_hint(self) -> str:
    return '\n'.join((self.text, '~' * self.column + '^'))

  def __str__(self) -> str:
    lines = [
      '',
      f'  in {colored(self.filename, "blue")} at line {self.line}: {colored(self.message, "red")}',
      *('  |' + l for l in self.get_text_hint().splitlines()),
    ]
    return '\n'.join(lines)


@dataclass
class Closure:
  """
  Contains the definition of a closure in text format.
  """

  #: A unique ID for the closure, usually derived from the number of closures that have already
  #: been parsed in the same file or it's parent closures.
  id: str

  #: The line number where the closure begins.
  line: int

  #: The indentation of the closure's body. For a single expression, this represents the
  #: offset of the expression in line.
  indent: int

  #: The parameter names of the closure. May be `None` to indicate that closure had no header.
  parameters: t.Optional[t.List[str]]

  #: The body of the closure. May be `None` if the closure body is not constructed using curly
  #: braces to encapsulate multiple statements. In that case, the #expr field is set instead.
  body: t.Optional[str]

  #: Only set if the body of the closure is just an expression.
  expr: t.Optional[str]


@dataclass
class RewriteResult:
  #: The rewritten Python code.
  code: str

  #: The closures extracted from the code.
  closures: t.Dict[str, Closure]


class Rewriter:

  UNARY_OPERATORS = frozenset(['not', '~'])
  BINARY_OPERATORS = frozenset(['-', '+', '*', '**', '/', '//', '^', '|', '&', '.', '==', '<=', '>=', '<', '>', 'is', '%'])
  PYTHON_BLOCK_KEYWORDS = frozenset(['class', 'def', 'if', 'elif', 'else', 'for', 'while', 'with'])

  def __init__(self, text: str, filename: str, supports_local_def: bool) -> None:
    """
    # Arguments
    text: The Craftr DSL code to parse and turn into an AST-like structure.
    filename: The filename where the DSL code is from.
    supports_local_def: Whether the `def varname = ...` syntax is allowed and understood. This is an important
      syntax feature when enabling the #NameRewriter with #TranspileOptions.closure_target.
    """

    self.tokenizer = Tokenizer(rule_set, text)
    self.filename = filename
    self.supports_local_def = supports_local_def
    self._closure_stack: t.List[str] = []  #: Used to construct nested closure names.
    self._closure_counter = 0  #: Used to assign a unique number to every closure.
    self._closures: t.Dict[str, Closure] = {}

  @contextlib.contextmanager
  def _playing_games(self) -> t.Iterator[t.Callable[[], None]]:
    """
    Context manager to save the current tokenizer and closure state and restore it on exit. This is
    useful for lookaheads, like :meth:`_test_dict`. If the returned callable is called, the
    tokenizer and closure state is not restored.
    """

    state = self.tokenizer.state
    closure_state = self._closure_counter, self._closures.copy(), self._closure_stack[:]
    do_restore = True
    def commit():
      nonlocal do_restore
      do_restore = False
    try:
      yield commit
    finally:
      if do_restore:
        self.tokenizer.state = state
        self._closure_counter, self._closures, self._closure_stack = closure_state

  def _syntax_error(self, msg: str, pos: t.Optional[Cursor] = None) -> SyntaxError:
    """ Raise a syntax error on the current position of the tokenizer, or the specified *pos*. """

    pos = pos or self.tokenizer.current.pos
    text = self.tokenizer.scanner.getline(pos)
    return SyntaxError(msg, self.filename, pos.line, pos.column, text)

  def _consume_whitespace(self, newlines: t.Union[bool, ParseMode] = False, reset_to_indent: bool = True) -> str:
    """
    Consumes whitespace, indents, comments, and, if enabled, newlines until a different token is
    encountered. If *reset_to_indent* is enabled (default) then the tokenizer will be moved back
    to the indent token before that different token.
    """

    if isinstance(newlines, ParseMode):
      newlines = bool(newlines & ParseMode.GROUPED)

    token = ProxyToken(self.tokenizer)
    parts: t.List[str] = []
    state = token.save()
    while token.is_ignorable(newlines):
      parts.append(token.value)
      state = token.save()
      token.next()
    if reset_to_indent and state.token and state.token.type == Token.Indent:
      token.load(state)
      parts.pop()
    return ''.join(parts)

  def _parse_closure(self) -> t.Optional[Closure]:
    """
    Attempts to parse a closure at the current position of the tokenizer. Closures can have the
    following syntactical variants:

    1. `() -> { stmts }`
    2. `arg -> { stmts }`
    3. `(arg1, arg2) -> { stmts }`
    4. `{ stmts }`

    Closures of the fourth form can conflict syntactically with Python set literals and will thus
    override the native syntactic feature. The fourth form also results in the #node.Closure
    parameter's list to be `None`.

    The first to third form may also exist without curly braces to define a single expression
    as the closure body (returning the value of that expression from the closure).

    1. `() -> expr`
    2. `arg -> expr`
    3. `(arg1, arg2) -> expr`

    Returns #None if no closure can be parsed at the current position of the tokenizer.
    """

    token = ProxyToken(self.tokenizer)
    pos = token.pos
    state = token.save()
    arglist = self._parse_closure_header()
    body: t.Optional[str] = None
    expr: t.Optional[str] = None
    closure_id = ''.join(self._closure_stack) + f'_closure_{self._closure_counter + 1}'
    self._closure_stack.append(closure_id)

    if token.tv == (Token.Control, '{'):
      body = self._parse_closure_body()
    if body is None and arglist is not None:
      # We only parse an expression for the Closure body if an arglist was specified.
      expr = self._rewrite_expr(mode=ParseMode.DEFAULT)

    assert self._closure_stack.pop() == closure_id

    if not (body or expr):
      # NOTE(NiklasRosenstein): We could raise our own SyntaxError here if an arglist was provided
      #     as that is a strong indicator that a Closure expression or body should be provided,
      #     but we can also just leave the complaining to the Python parser.
      token.load(state)
      return None

    self._closure_counter += 1
    return Closure(closure_id, pos.line, pos.column, arglist, body, expr)

  def _parse_closure_body(self) -> t.Optional[str]:
    """
    Parses the body of a closure and returns it's code. Expects the tokenizer to point to the
    opening curly brace of the closure.
    """

    token = ProxyToken(self.tokenizer)
    assert token.tv == (Token.Control, '{'), token
    token.next()

    code = self._consume_whitespace(True)
    if '\n' in code:  # Multiline closure
      code += self._rewrite_stmt_block() + self._consume_whitespace(True, False)
    else:  # Singleline closure
      while token.type != Token.Newline and token.tv != (Token.Control, '}'):
        code += self._rewrite_stmt_singleline() + self._consume_whitespace(True, False)

    if token.tv != (Token.Control, '}'):
      raise self._syntax_error('expected closure closing brace')

    token.next()
    return code

  def _parse_closure_header(self) -> t.Optional[t.List[str]]:
    """
    Handles the possible formats for a closure header, f.e. a single argument name or an arglist
    followed by an arrow (`->`). Returns `None` if there can be no closure header extracted from
    the current position of the lexer.
    """

    token = ProxyToken(self.tokenizer)
    state = token.save()

    with token.set_skipped(Token.Whitespace):
      arglist: t.Optional[t.List[str]] = None
      if token.tv == (Token.Control, '('):
        arglist = self._parse_closure_arglist()
      elif token.type == Token.Name:
        arglist = [token.value]
        token.next()

      if arglist is None or token.tv != (Token.Control, '->'):
        # We may have found something that looks like an arglist, but isn't, or we found an
        # arglist but no following arrow, so we go back to where we started and let someone
        # else handle these tokens.
        token.load(state)
        return None

      token.next()
      return arglist

  def _parse_closure_arglist(self) -> t.Optional[t.List[str]]:
    """
    This method expects an open parenthesis as the current token and attempts to extract a list of
    argument names. Returns `None` if no argument list was actually extracted.
    """

    token = ProxyToken(self.tokenizer)
    assert token.tv == (Token.Control, '('), token

    state = token.save()
    begin = token.pos.offset
    with token.set_skipped({Token.Whitespace, Token.Comment, Token.Newline, Token.Indent}):
      token.next()

      arglist: t.List[str] = []
      is_delimited = True

      while token.tv != (Token.Control, ')'):

        if (not is_delimited  # Token is not preceeded by an opening parentheses or comma.
            or token.type != Token.Name):  # We can only accept a name at this position.
          token.load(state)
          return None

        arglist.append(token.value)
        token.next()
        is_delimited = (token.tv == (Token.Control, ','))
        if is_delimited:
          token.next()

      assert token.tv == (Token.Control, ')'), token

      token.next()
      return arglist

  def _rewrite_expr(self, mode: ParseMode) -> str:
    """
    Consumes a Python expression and returns it's code. Does not parse over a comma.

    :param mode: The current parse mode that provides context about the level that is currently
      being parsed.
    """

    code = self._consume_whitespace(mode)
    code += self._rewrite_atom(mode)

    token = ProxyToken(self.tokenizer)
    while token:
      code += self._consume_whitespace(mode)

      if token.type == Token.Control and token.value in self.BINARY_OPERATORS:
        code += token.value
        token.next()
        code += self._rewrite_expr(mode)

      elif token.is_control('(['):
        code += self._rewrite_atom(ParseMode.FUNCTION_CALL | ParseMode.GROUPED if token.value == '(' else ParseMode.DEFAULT)

      else:
        break

    return code

  def _rewrite_items(self, mode: ParseMode) -> str:
    """
    Rewrites expressions separated by commas.
    """

    token = ProxyToken(self.tokenizer)
    code = ''
    while True:
      code += self._consume_whitespace(mode)
      code += self._rewrite_expr(mode=mode)
      code += self._consume_whitespace(mode)
      if mode & ParseMode.CALL_ARGS and token.is_control('='):
        code += '='
        token.next()
        # TODO(NiklasRosenstein): This may be problematic in unparenthesised calls?
        code += self._rewrite_expr(mode=mode)
      if not token.is_control(','):
        break
      code += ','
      token.next()
    return code

  def _rewrite_atom(self, mode: ParseMode = ParseMode.DEFAULT) -> str:
    """
    Consumes a Python or Craftr DSL language atom and returns it rewritten as pure Python code. If
    a closure is encountered, it will be replaced with a name reference and the closure itself will
    be stored in the #_closures mapping.
    """

    token = ProxyToken(self.tokenizer)

    if token.is_control('{') and self._test_dict():
      return self._rewrite_dict()

    code = ''
    if closure := self._parse_closure():
      code += closure.id
      self._closures[closure.id] = closure

    elif token.is_control('([{'):
      assert not (mode & ParseMode.FUNCTION_CALL) or token.is_control('('), \
          'ParseMode.FUNCTION_CALL requires current token be opening parenthesis'

      expected_close_token = {'(': ')', '[': ']', '{': '}'}[token.value]
      code += token.value
      token.next()
      code += self._consume_whitespace(True)
      if not token.is_control(expected_close_token):
        new_mode = ParseMode.CALL_ARGS if mode & ParseMode.FUNCTION_CALL else ParseMode.DEFAULT
        code += self._rewrite_items(new_mode | ParseMode.GROUPED)
      if not token.is_control(expected_close_token):
        raise self._syntax_error(f'expected {expected_close_token} but got {token}')

      code += expected_close_token
      token.next()

    elif mode & ParseMode.CALL_ARGS and (token.is_control(['*', '**'])):
      code += token.value
      token.next()
      code += self._rewrite_expr(mode=ParseMode.DEFAULT)

    elif token.type in (Token.Name, Token.Literal):
      code += token.value
      token.next()

    elif token.type == Token.Control and token.value in self.UNARY_OPERATORS:
      code += token.value
      token.next()
      code += self._rewrite_expr(mode=mode)
      return code

    else:
      raise self._syntax_error(f'not sure how to deal with {token} {mode}')

    return code

  def _test_dict(self) -> bool:
    """
    Tests if the code from the current opening curly brace looks like a dictionary definition.
    """

    token = ProxyToken(self.tokenizer)
    assert token.is_control('{'), False

    with self._playing_games():
      token.next()
      self._consume_whitespace(True, False)
      try:
        self._rewrite_expr(mode=ParseMode.GROUPED)
        self._consume_whitespace(True, False)
        return token.is_control(':')
      except SyntaxError:
        return False

  def _rewrite_dict(self) -> str:
    token = ProxyToken(self.tokenizer)
    assert token.is_control('{'), token
    token.next()
    code = '{'

    while not token.is_control('}'):
      code += self._consume_whitespace(True, False)
      code += self._rewrite_expr(mode=ParseMode.GROUPED)
      code += self._consume_whitespace(True, False)
      if not token.is_control(':'):
        raise self._syntax_error('expected :')
      code += ':'
      token.next()
      code += self._consume_whitespace(True, False)
      code += self._rewrite_expr(mode=ParseMode.GROUPED)
      code += self._consume_whitespace(True, False)
      if not token.is_control(','):
        break
      code += ','
      token.next()
      code += self._consume_whitespace(True, False)

    if not token.is_control('}'):
      raise self._syntax_error('expected }')

    token.next()
    return code + '}'

  def _rewrite_stmt_singleline(self) -> str:
    token = ProxyToken(self.tokenizer)
    code = self._consume_whitespace(False)

    if token.type == Token.Name and token.value == 'pass':
      token.next()
      return code + 'pass' + self._consume_whitespace(True)

    elif token.type == Token.Name and token.value in ('assert', 'return', 'yield'):
      code += token.value
      is_yield = token.value == 'yield'
      token.next()
      code += self._consume_whitespace(False)
      if is_yield and token.tv == (Token.Name, 'from'):
        code += token.value
        token.next()
      code += self._rewrite_items(ParseMode.DEFAULT) + self._consume_whitespace(True)
      return code

    elif token.type == Token.Name and token.value in ('import', 'from'):
      while token.type != Token.Newline and token.tv != (Token.Control, ';'):
        code += token.value
        token.next()
      code += token.value
      token.next()
      return code

    else:
      return code + self._rewrite_stmt_line_expr_or_assign()

  def _rewrite_stmt_line_expr_or_assign(self) -> str:
    token = ProxyToken(self.tokenizer)
    code = self._rewrite_items(ParseMode.DEFAULT)
    code += self._consume_whitespace(newlines=False)

    if token.tv == (Token.Control, '='):  # Assignment
      token.next()
      code += '=' + self._consume_whitespace(newlines=False) + self._rewrite_items(ParseMode.DEFAULT)

    elif token and not token.is_ignorable(True) and not token.is_control(')]}:'):  # Unparenthesises functionc all
      if code[-1].isspace():
        code = code[:-1]
      # TODO(NiklasRosenstein): We may want to indicate here that we're parsing call arguments,
      #   but that the call is not parenthesised.
      code += '(' + self._rewrite_items(ParseMode.CALL_ARGS) + ')'

    return code + self._consume_whitespace(True)

  def _test_local_def(self) -> t.Optional[str]:
    """
    Tests if the current `def` keyword introduces a local variable assignment, and if so,
    returns the code for the rewritten code for the entire assignment.
    """

    token = ProxyToken(self.tokenizer)
    assert token.tv == (Token.Name, 'def'), token

    with self._playing_games() as commit:
      token.next()
      self._consume_whitespace(False)
      if token.type != Token.Name:
        return None
      code = '_def_' + token.value
      token.next()
      code += self._consume_whitespace(False)
      if not token.is_control('='):
        return None
      code += token.value
      token.next()
      code += self._rewrite_expr(ParseMode.DEFAULT)
      commit()
      return code

  def _rewrite_stmt(self, indentation: int) -> str:
    """
    Parses a line statement of Python code. Returns an empty string if the actual indendation of
    the code is lower than *indentation*. Handles parsing of Python block statements (such as if,
    try, etc.) recursively.
    """

    code = self._consume_whitespace(True)

    token = ProxyToken(self.tokenizer)
    assert token.type == Token.Indent, token
    if len(token.value) < indentation:
      return ''
    elif len(token.value) > indentation:
      raise self._syntax_error('unexpected indentation')

    code += token.value
    token.next()

    if self.supports_local_def and token.tv == (Token.Name, 'def') and (defcode := self._test_local_def()):
      return code + defcode

    if token.type == Token.Name and token.value in self.PYTHON_BLOCK_KEYWORDS:
      # Parse to the next colon.
      # TODO(nrosenstein): If we want to support Craftr DSL syntax in the expressions of block
      #   statements, we'll need to rewrite them on a more granular level.
      while token and token.tv not in ((Token.Newline, '\n'), (Token.Control, ':')):
        code += token.value
        token.next()
      if token.tv != (Token.Control, ':'):
        raise self._syntax_error(f'expected semicolon, found {token}')
      code += ':'
      token.next()

      return code + self._rewrite_stmt_block(indentation)

    else:
      return code + self._rewrite_stmt_singleline()

  def _rewrite_stmt_block(self, parent_indentation: t.Optional[int] = None) -> str:
    """
    Rewrites an entire statement block and returns it's rewritten code.
    """

    token = ProxyToken(self.tokenizer)
    code = self._consume_whitespace(True)
    if not token:
      return code
    assert token.type == Token.Indent, token
    if parent_indentation is not None and len(token.value) <= parent_indentation:
      raise self._syntax_error(f'expected indent > {parent_indentation}, found {token}')
    indentation = len(token.value)
    while token and (stmt := self._rewrite_stmt(indentation)):
      code += stmt + self._consume_whitespace(True)
    return code

  def rewrite(self) -> RewriteResult:
    return RewriteResult(self._rewrite_stmt_block(), self._closures)

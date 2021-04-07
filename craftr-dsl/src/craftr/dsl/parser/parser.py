
"""
Parser that converts Craftr DSL code into an extended Python AST that can be transpiled into a pure
AST using the #.transpiler module.
"""

import abc
import ast
import enum
import logging
import pdb
import typing as t

import astor
from nr.parsing.core import rules
from nr.parsing.core.scanner import Cursor
from nr.parsing.core.tokenizer import ProxyToken, RuleSet, Tokenizer

from . import nodes


def syntax_error(msg: str, filename: str, line: int, col: int, text: str, cls = SyntaxError) -> Exception:
  return cls(msg, (filename, line, col, text))


class Token(enum.Enum):
  Eof = enum.auto()
  Indent = enum.auto()
  Whitespace = enum.auto()
  Newline = enum.auto()
  Comment = enum.auto()
  Name = enum.auto()
  Literal = enum.auto()
  Control = enum.auto()

  def ignorable(self) -> bool:
    return self in (Token.Indent, Token.Whitespace, Token.Comment)


rule_set = RuleSet((Token.Eof, ''))
rule_set.rule(Token.Indent, rules.regex_extract(r'[\t ]*', at_line_start_only=True))
rule_set.rule(Token.Newline, rules.regex_extract(r'\n'))
rule_set.rule(Token.Whitespace, rules.regex_extract(r'\s+'))
rule_set.rule(Token.Comment, rules.regex_extract(r'#.*'))
rule_set.rule(Token.Name, rules.regex_extract(r'[A-Za-z\_][A-Za-z0-9\_]*'))
rule_set.rule(Token.Literal, rules.regex_extract(r'[+\-]?(\d+)(\.\d*)?'))
rule_set.rule(Token.Literal, rules.string_literal())
rule_set.rule(Token.Control, rules.regex_extract(
  r'(\[|\]|\{|\}|\(|\)|<<|<|>>|>|\.|,|\->|\-|!|\+|\*|//|/|->|==|=|:|&|\||^|%|@|;)'))


class Macro(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def parse(self, tokenizer: 'CraftrParser', expect_expression: bool) -> t.Union[ast.expr, t.List[ast.stmt]]:
    pass


class CraftrParser:

  log = logging.getLogger(__module__ + '.' + __qualname__)  # type: ignore

  BINARY_OPERATORS = frozenset(['-', '+', '*', '**', '/', '//', '^', '|', '&', '.'])
  PYTHON_BLOCK_KEYWORDS = frozenset(['class', 'def', 'if', 'elif', 'else', 'for', 'while', 'with'])
  PYTHON_KEYWORDS = frozenset(['assert', 'pass']) | PYTHON_BLOCK_KEYWORDS
  EXPRESSION_DELIMITERS = frozenset([(Token.Newline, '\n'), (Token.Control, ';')])

  def __init__(self, text: str, filename: str) -> None:
    self.tokenizer = Tokenizer(rule_set, text)
    self.filename = filename
    self._closure_stack: t.List[str] = []  #: Used to construct nested closure names.
    self._closure_counter = 0  #: Used to assign a unique number to every closure.
    self._closures: t.Dict[str, nodes.Closure] = {}

  def _syntax_error(self, msg: str, pos: t.Optional[Cursor] = None) -> SyntaxError:
    pos = pos or self.tokenizer.current.pos
    return syntax_error(
        msg=msg,
        filename=self.filename,
        line=pos.line,
        col=pos.column + 1,
        text=self.tokenizer.scanner.getline(pos))

  def _parse_closure(self) -> t.Optional[nodes.Closure]:
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
    state = token.save()
    arglist = self._parse_closure_header()
    body: t.Optional[t.List[ast.stmt]] = None
    expr: t.Optional[ast.expr] = None
    closure_id = ''.join(self._closure_stack) + f'_closure_{self._closure_counter + 1}'
    self._closure_stack.append(closure_id)

    if token.tv == (Token.Control, '{'):
      body = self._parse_closure_body()
    if body is None and arglist is not None:
      # We only parse an expression for the Closure body if an arglist was specified.
      expr = self._rewrite_expr()

    assert self._closure_stack.pop() == closure_id

    if not (body or expr):
      # NOTE(NiklasRosenstein): We could raise our own SyntaxError here if an arglist was provided
      #     as that is a strong indicator that a Closure expression or body should be provided,
      #     but we can also just leave the complaining to the Python parser.
      token.load(state)
      return None

    self._closure_counter += 1
    return nodes.Closure(closure_id, arglist, body, expr)

  def _parse_closure_body(self) -> str:
    token = ProxyToken(self.tokenizer)
    state = token.save()

    if token.tv != (Token.Control, '{'):
      return None
    token.next()

    code = self._rewrite_stmt_block(-1) + self._consume_whitespace(True)

    if token.type == Token.Indent:
      code += token.value
      token.next()

    if token.tv != (Token.Control, '}'):
      token.load(state)
      return None
    token.next()

    return code

  def _parse_closure_header(self) -> t.Optional[t.List[str]]:
    """
    Handles the possible formats for a closure header, i.e. a single argument name or an arglist
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
    state = token.save()

    if token.tv != (Token.Control, '('):
      return None

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

      token.next()
      return arglist

  def _rewrite_expr(self, comma_break: bool = True, parenthesised: bool = False) -> str:
    """
    Consumes a Python expression and returns it's code.
    """

    token = ProxyToken(self.tokenizer)
    code = self._consume_whitespace(parenthesised) + self._rewrite_atom() + self._consume_whitespace(parenthesised)

    binary_operators = self.BINARY_OPERATORS
    if not comma_break:
      binary_operators = binary_operators | set(',')

    while True:
      code += self._consume_whitespace(parenthesised)
      if not token:
        break

      if token.type == Token.Control and token.value in binary_operators:
        code += token.value
        token.next()
        code += self._rewrite_expr(comma_break, parenthesised)

      elif token.type == Token.Control and token.value in '([':
        code += self._rewrite_atom()

      else:
        break

    return code

  def _rewrite_atom(self):
    """
    Consumes a Python or Craftr DSL language atom and returns it rewritten as pure Python code. If
    a closure is encountered, it will be replaced with a name reference and the closure itself will
    be stored in the #_closures mapping.
    """

    token = ProxyToken(self.tokenizer)
    code = ''

    if closure := self._parse_closure():
      code += closure.id
      self._closures[closure.id] = closure

    elif token.type == Token.Control and token.value in '([{':
      expected_close_token = {'(': ')', '[': ']', '{': '}'}[token.value]
      code += token.value
      token.next()
      code += self._rewrite_expr(comma_break=False, parenthesised=True)
      if token.type != Token.Control or token.value != expected_close_token:
        raise SyntaxError(f'_rewrite_atom: Expected {expected_close_token} but got {token}')
      code += expected_close_token
      token.next()

    elif token.type in (Token.Name, Token.Literal):
      code += token.value
      token.next()

    else:
      raise SyntaxError(f'_rewrite_atom: Not sure what to do with {token}')

    return code

  def _consume_whitespace(self, skip_newlines: bool = False) -> str:
    token = ProxyToken(self.tokenizer)
    parts: t.List[str] = []
    state = token.save()
    while token.type.ignorable() or (skip_newlines and token.type == Token.Newline):
      parts.append(token.value)
      state = token.save()
      token.next()
    if state.token and state.token.type == Token.Indent:
      token.load(state)
      parts.pop()
    return ''.join(parts)

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

    code += token.value
    token.next()

    if token.type == Token.Name and token.value in self.PYTHON_BLOCK_KEYWORDS:
      # Parse to the next colon.
      # TODO(nrosenstein): If we want to support Craftr DSL syntax in the expressions of block
      #   statements, we'll need to rewrite them on a more granular level.
      while token and token.tv not in ((Token.Newline, '\n'), (Token.Control, ':')):
        code += token.value
        token.next()
      if token.tv != (Token.Control, ':'):
        raise SyntaxError(f'_rewrite_stmt: expected semicolon, found {token}')
      code += ':'
      token.next()

      return code + self._rewrite_stmt_block(indentation)

    elif token.type == Token.Name and token.value == 'pass':
      token.next()
      return code + 'pass' + self._consume_whitespace(True)

    # TODO(nrosenstein): assert?

    else:
      code += self._rewrite_expr(comma_break=False) + self._consume_whitespace()
      if token.tv == (Token.Control, '='):
        token.next()
        code += '=' + self._consume_whitespace() + self._rewrite_expr(comma_break=False)
      elif token.type != Token.Newline and not token.type.ignorable():
        if code[-1].isspace():
          code = code[:-1]
        code += '(' + self._rewrite_expr(comma_break=False) + ')'

      return code + self._consume_whitespace(True)

  def _rewrite_stmt_block(self, parent_indentation: int) -> str:
    token = ProxyToken(self.tokenizer)
    code = self._consume_whitespace(True)
    assert token.type == Token.Indent, token
    if parent_indentation >= 0 and len(token.value) <= parent_indentation:
      raise SyntaxError(f'_rewrite_stmt: expected indent > {parent_indentation}, found {token}')
    indentation = len(token.value)
    while stmt := self._rewrite_stmt(indentation):
      code += stmt
    return code

  def parse(self) -> ast.Module:
    while self.tokenizer:
      print(self._rewrite_stmt(0))
    print(self._closures.keys())
    exit()
    code = self._rewrite_body(-1)
    print('Final code:\n')
    print(code)
    #stmts: t.List[ast.stmt] = []
    #while self.tokenizer:
    #  expr = self._rewrite_expr()
    #  print(repr(expr))
    #  if self.tokenizer.current.type == Token.Newline or self.tokenizer.current.tv == (Token.Control, '='):
    #    self.tokenizer.next()
    exit()
    return ast.Module(stmts)

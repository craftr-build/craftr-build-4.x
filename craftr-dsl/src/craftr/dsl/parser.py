
import astor  # type: ignore
import ast as pyast
import enum
import os
import re
import textwrap
import typing as t

from nr.functional import flatmap
from nr.parsing.core import Cursor, Scanner, Lexer, Rule, Regex, Charset, TokenizationError  # type: ignore

from . import ast, util
from .macros import MacroPlugin


class Token(enum.Enum):
  INDENT = enum.auto()
  WHITESPACE = enum.auto()
  NEWLINE = enum.auto()
  COMMENT = enum.auto()
  NAME = enum.auto()
  LITERAL = enum.auto()
  CONTROL = enum.auto()


class PyParseMode(enum.Enum):
  #: Consume all tokens that could reasonably be part of the expression.
  DEFAULT = enum.auto()

  #: Expect the parantheses of a call and only parse to the closing parentheses.
  CALL = enum.auto()

  #: Stop at the first comma encountered at the top-level.
  ARGUMENT = enum.auto()

  #: Parse a full statement until an unexpected token is found.
  EXEC = enum.auto()


class LambdaRule(Rule):

  def __init__(self, name, func, skip=False):
    super().__init__(name, skip)
    self.func = func

  def tokenize(self, scanner):
    return self.func(scanner)


class Parser:
  """
  This parser constructs an AST from Craftr DSL code.
  """

  @staticmethod
  def _tokenize_string_literal(scanner):
    prefix = scanner.match(r'[bfru]+') | flatmap(lambda m: m.group(0)) or ''  # type: ignore
    quote_type = scanner.match(r'("""|\'\'\'|"|\')') | flatmap(lambda m: m.group(0))  # type: ignore
    if not quote_type:
      return None
    contents = ''
    while scanner.char and scanner.char != '\n':
      if scanner.match(re.escape(quote_type)):
        break
      contents += scanner.char
      if scanner.char == '\\':
        contents += scanner.next()
      scanner.next()
    else:
      return None
    return prefix + quote_type + contents + quote_type

  RULES = [
    Regex(Token.COMMENT, r'#.*', group=0),
    Regex(Token.LITERAL, r'[+\-]?(\d+)(\.\d*)?', group=0),  # TODO: Binary, Octal, etc.
    Regex(Token.CONTROL, r'(\[|\]|\{|\}|\(|\)|<<|<|>>|>|\.|,|\->|\-|!|\+|\*|//|/|=>|==|=|:|&|\||^|%|@|;)', group=0),
    LambdaRule(Token.LITERAL, _tokenize_string_literal.__func__),  # type: ignore
    Regex(Token.NAME, r'[A-z\_][A-Za-z0-9\_]*', group=0),
    Charset(Token.INDENT, ' \t', at_column=0),
    Charset(Token.NEWLINE, '\n'),
    Charset(Token.WHITESPACE, ' \t'),
  ]

  def __init__(self,
    code: str,
    filename: str,
    macros: t.Optional[t.Dict[str, MacroPlugin]] = None,
  ) -> None:

    self._code = code
    self._filename = filename
    self._macros = macros or {}
    self._lexer = Lexer(Scanner(code), self.RULES)
    self._lexer.next()
    self._lexer.disable(Token.WHITESPACE)

  def location(self) -> ast.Location:
    cursor = self._lexer.token.cursor
    return ast.Location(self._filename, cursor.index, cursor.lineno, cursor.colno)

  def error(self,
    ast_type: t.Type,
    token_type: t.Optional[Token] = None,
    value: t.Optional[str] = None,
    msg: t.Optional[str] = None,
    cursor: t.Optional[Cursor] = None,
  ) -> t.NoReturn:
    """
    Helper function to raise a #SyntaxError during parsing for when a specific type of token was
    expected but another was found.
    """

    cursor = cursor or self._lexer.token.cursor
    message = f'while parsing <{ast_type.__name__}>,'
    if token_type is not None:
      message += f' expected {token_type}'
      if value is not None:
        message += f' ({value!r})'
      message += f', found {self._lexer.token.type} ({self._lexer.token.value!r})'
    elif msg:
      message += ' ' + msg
    else:
      message += ' was unable to tokenize stream'
    line = (self._code.splitlines() + [''])[cursor.lineno - 1]
    raise SyntaxError(message, (self._filename, cursor.lineno, cursor.colno, line))

  def parse_indent(self) -> int:
    indent = 0
    while True:  # Skip over empty lines with indents
      if self._lexer.token.type == Token.INDENT:
        indent = len(self._lexer.token.value)
        self._lexer.next()
      if self._lexer.token.type == Token.COMMENT:
        self._lexer.next()
      if self._lexer.token.type == Token.NEWLINE:
        self._lexer.next()
        continue
      return indent

  def parse_target(self) -> ast.Target:
    loc = self.location()
    names = []
    while self._lexer.token.type == Token.NAME:
      names.append(self._lexer.token.value)
      self._lexer.next()
      if self._lexer.token.tv != (Token.CONTROL, '.'):
        break
      self._lexer.next()
    if not names:
      self.error(ast.Target, Token.NAME)
    return ast.Target(loc, '.'.join(names))

  def parse_assign(self, target: ast.Target) -> ast.Assign:
    if self._lexer.token.tv != (Token.CONTROL, '='):
      self.error(ast.Assign, Token.CONTROL, '=')
    self._lexer.next()
    return ast.Assign(target.loc, target, self.parse_expr())

  def parse_let(self) -> ast.Let:
    assert self._lexer.token.tv == (Token.NAME, 'let')
    loc = self.location()
    self._lexer.next()
    if self._lexer.token.type != Token.NAME:
      self.error(ast.Let, Token.NAME)
    name = self._lexer.token.value
    self._lexer.next()
    assign = self.parse_assign(ast.Target(loc, name))
    return ast.Let(loc, assign.target, assign.value)

  def parse_python(self, mode: PyParseMode = PyParseMode.DEFAULT) -> t.Tuple[t.List[pyast.stmt], t.List[ast.Lambda]]:
    """
    Consumes all tokens for a Python expression and parses them with the #ast module. The parsing
    mode can be overwritten to change the behaviour slightly as to how which or how many tokens
    are consumed to construct the expression.
    """

    loc = self.location()
    lambdas: t.List[ast.Lambda] = []

    with self._lexer.enabled(Token.WHITESPACE):

      parts: t.List[str] = []
      stack: t.List[str] = []
      while self._lexer.token.type != 'eof':
        token = self._lexer.token
        if token.tv == (Token.CONTROL, ';'):
          self._lexer.next()
          break

        if not parts and mode == PyParseMode.CALL and token.tv != (Token.CONTROL, '('):
          self.error(ast.Expr, Token.CONTROL, '(')

        # Check if this is the beginning of a lambda expression.
        node = self.try_parse_lambda()
        if node is not None:
          lambdas.append(node)
          if parts:
            # TODO(NiklasRosenstein): Maybe only need to do this when there exists code on
            #     the same line already.
            parts.append(' ')
          parts.append(node.id)
          continue

        # Check if this is a macro.
        if token.tv == (Token.CONTROL, '!'):
          token = self._lexer.next()
          if token.type != Token.NAME:
            self.error(pyast.expr, Token.NAME, msg='expected macro name')
          if token.value not in self._macros:
            self.error(pyast.expr, msg=f'unknown macro: {token.value!r}')
          parts.append(astor.to_source(self._macros[token.value].parse_macro(self, self._lexer)))
          continue

        if token.type == Token.CONTROL and token.value in '([{':
          stack.append({'(': ')', '[': ']', '{': '}'}[token.value])
        elif token.type == Token.CONTROL and token.value in ')]}':
          if not stack:
            #self._lexer.next()
            break
          if stack[-1] != token.value:
            self.error(ast.Expr, Token.CONTROL, stack[-1])  # Unbalanced parenthesis
          stack.pop()
        elif mode != PyParseMode.EXEC and token.type == Token.NEWLINE:
          if not stack:
            break
        elif mode == PyParseMode.ARGUMENT and token.tv == (Token.CONTROL, ',') and not stack:
          break
        elif mode == PyParseMode.CALL and not stack:
          break
        parts.append(token.value)
        try:
          self._lexer.next()
        except TokenizationError:
          self.error(ast.Expr)

    # Adjust the code's line number and offset accordingly. This is really hacky.
    code = ''.join(parts)
    requires_wrapper = mode == PyParseMode.EXEC and textwrap.dedent(code) != code
    if requires_wrapper:
      code = '\n' * (loc.lineno - 1) + 'def body():\n' + code
    else:
      code = '\n' * (loc.lineno - 1) + code
    parse_mode = 'exec' if mode == PyParseMode.EXEC else 'eval'
    pyast_node = pyast.parse(code, mode=parse_mode, filename=self._filename)

    if requires_wrapper:
      statements = t.cast(pyast.FunctionDef, t.cast(pyast.Module, pyast_node).body[0]).body
    else:
      statements = [t.cast(pyast.Expr, pyast_node)]

    return statements, lambdas

  def parse_expr(self, mode: PyParseMode = PyParseMode.DEFAULT) -> ast.Expr:
    """
    Parses a Python expression.
    """

    loc = self.location()
    if mode == PyParseMode.EXEC:
      raise ValueError(f'invalid mode for parse_expr(): {mode}')

    stmts, lambdas = self.parse_python(mode)
    assert len(stmts) == 1
    assert isinstance(stmts[0], pyast.Expression)
    return ast.Expr(loc, lambdas, stmts[0])

  def try_parse_lambda(self) -> t.Optional[ast.Lambda]:
    loc = self.location()
    checkpoint = self._lexer.checkpoint()
    try:
      lambda_header = self.parse_lambda_header()
    except SyntaxError:
      self._lexer.restore(checkpoint)
      return None

    # Generate a unique ID for the lambda.
    filename = os.path.basename(self._filename)
    filename = re.sub(r'[^A-z0-9\_]+', '_', filename).strip('_')
    lambda_id = f'lambda_{filename}_{loc.lineno}_{loc.colno}'

    # Parse the lambda body and construct a function definition node from it.
    func_def = self.parse_lambda_body(loc, lambda_id, lambda_header)
    return ast.Lambda(loc, lambda_id, func_def)

  def parse_lambda_header(self) -> t.List[str]:
    """
    Parses the DSL lambda header, expecting a list of arguments or a single name followed by a
    lambda arrow. Leaves the lexer positioned on the opening brace of the lambda scope.
    """

    with self._lexer.disabled(Token.WHITESPACE):
      arglist: t.List[str] = []

      if self._lexer.token.tv == (Token.CONTROL, '('):
        self._lexer.next()
        while self._lexer.token.tv != (Token.CONTROL, ')'):
          if self._lexer.token.type != Token.NAME:
            self.error(ast.Expr, Token.NAME)
          if self._lexer.token.value in arglist:
            self.error(ast.Expr, msg='duplicate lambda argument name')
          arglist.append(self._lexer.token.value)
          self._lexer.next()
          if self._lexer.token.tv == (Token.CONTROL, ','):
            self._lexer.next()
          elif self._lexer.token.tv != (Token.CONTROL, ')'):
            self.error(ast.Expr, Token.CONTROL, ',)')
        self._lexer.next()

      elif self._lexer.token.type == Token.NAME:
        arglist.append(self._lexer.token.value)
        self._lexer.next()

      else:
        self.error(ast.Expr, msg='expected lambda header')

      if self._lexer.token.tv != (Token.CONTROL, '=>'):
        self.error(ast.Expr, Token.CONTROL, '=>')
      self._lexer.next()

      if self._lexer.token.tv != (Token.CONTROL, '{'):
        self.error(ast.Expr, Token.CONTROL, '{')

      return arglist

  def parse_lambda_body(self, loc: ast.Location, name: str, argument_names: t.List[str]) -> pyast.FunctionDef:
    """
    Parses the body of a lambda.
    """

    if self._lexer.token.tv != (Token.CONTROL, '{'):
      self.error(ast.Expr, Token.CONTROL, '{')
    self._lexer.next()

    lines: t.List[str] = []
    stmts, lambdas = self.parse_python(PyParseMode.EXEC)
    if self._lexer.token.tv != (Token.CONTROL, '}'):
      self.error(pyast.FunctionDef, Token.CONTROL, '}')
    self._lexer.next()

    return util.function_def(
      name,
      argument_names,
      [x.fdef for x in lambdas] + stmts,  # type: ignore
      lineno=loc.lineno,
      col_offset=loc.colno)

  def parse_statement(self) -> t.Optional[ast.Node]:
    """
    Parses a statement from the current position of the lexer. If no statement can be parsed from
    the current position, the method returns #None.
    """

    indent = self.parse_indent()

    if self._lexer.token.type == Token.NAME:
      if self._lexer.token.value == 'let':
        return self.parse_let()

      target = self.parse_target()
      is_call = False
      lambdas: t.List[ast.Lambda] = []
      args: t.Optional[t.List[pyast.expr]] = None
      body: t.List[ast.Node] = []

      if self._lexer.token.tv == (Token.CONTROL, '('):
        is_call = True
        expr = self.parse_expr(PyParseMode.CALL)
        if isinstance(expr.expr.body, pyast.Tuple):
          args = expr.expr.body.elts
        else:
          args = [expr.expr.body]
        lambdas += expr.lambdas

      if self._lexer.token.tv == (Token.CONTROL, '{'):
        is_call = True
        self._lexer.next()
        while self._lexer.token.tv != (Token.CONTROL, '}'):
          node = self.parse_statement()
          if not node:
            assert self._lexer.token.tv == (Token.CONTROL, '}')
            break
          body.append(node)
        self._lexer.next()

      if not is_call:
        return self.parse_assign(target)

      return ast.Call(target.loc, target, lambdas, args, body)

    else:
      return None

  def parse(self) -> ast.Module:
    loc = self.location()
    nodes: t.List[ast.Node] = []
    while self._lexer.token:
      node = self.parse_statement()
      if not node:
        break
      nodes.append(node)
    return ast.Module(loc, nodes)

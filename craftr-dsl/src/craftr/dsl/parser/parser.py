
"""
Parser that converts Craftr DSL code into an extended Python AST that can be transpiled into a pure
AST using the #.transpiler module.
"""

import abc
import ast
import enum
import logging
import typing as t

import astor
from nr.parsing.core import rules
from nr.parsing.core.tokenizer import ProxyToken, RuleSet, Tokenizer

from . import nodes


indent = 0
def traceable(func):
  import functools
  @functools.wraps(func)
  def _wrapper(self, *args, **kwargs):
    global indent
    #print(f'{"  " * indent}{func.__name__} {{', self.tokenizer.current)
    indent += 1
    try:
      result = func(self, *args, **kwargs)
    finally: indent -= 1
    #print(f'{"  " * indent}{func.__name__} }} -> {result!r}')
    return result
  return _wrapper


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


rule_set = RuleSet((Token.Eof, ''))
rule_set.rule(Token.Indent, rules.regex_extract(r'[\t ]*', at_line_start_only=True))
rule_set.rule(Token.Newline, rules.regex_extract(r'\n'))
rule_set.rule(Token.Whitespace, rules.regex_extract(r'\s+'))
rule_set.rule(Token.Comment, rules.regex_extract(r'#.*'))
rule_set.rule(Token.Name, rules.regex_extract(r'[A-z\_][A-Za-z0-9\_]*'))
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

  PYTHON_KEYWORDS = frozenset(('assert', 'def', 'class', 'for', 'while', 'if', 'with', 'try', 'pass'))
  EXPRESSION_DELIMITERS = frozenset([(Token.Newline, '\n'), (Token.Control, ';')])

  def __init__(self, text: str, filename: str) -> None:
    self.tokenizer = Tokenizer(rule_set, text)
    self.filename = filename
    self._closure_stack: t.List[str] = []  #: Used to construct nested closure names.
    self._closure_counter = 0  #: Used to assign a unique number to every closure.

  def _error(self, *args) -> t.NoReturn:
    raise RuntimeError(args)

  def _skip_comments(self) -> int:
    """
    Skips over comments and any preceeding whitespace. Returns the number of lines skipped. Does
    not skip the last #Token.Indent token at the end of the skippable token sequence.
    """

    token = ProxyToken(self.tokenizer)
    state = token.save()
    num_lines_skipped = 0
    while token.type in (Token.Comment, Token.Whitespace, Token.Newline, Token.Indent):
      if token.type == Token.Newline:
        num_lines_skipped += 1
      state = token.save()
      token.next()
    if state.token and state.token.type == Token.Indent:
      token.load(state)
    return num_lines_skipped

  def _parse_indent(self) -> int:
    """
    Skips over whitespace until a non-whitespace token is found and returns the depth of the
    indentation for that token.
    """

    indent = 0
    while self.tokenizer.current.type in (Token.Indent, Token.Comment, Token.Newline):
      if self.tokenizer.current.type == Token.Indent:
        indent = len(self.tokenizer.current.value)
      self.tokenizer.next()
      if self.tokenizer.current.type != Token.Newline:
        break
    return indent

  def _parse_expr(self) -> t.Optional[ast.expr]:  # NOSONAR
    """
    Parses a Python expression incl. Craftr closures.

    The stop condition for an expression is

    Implementation details: Closures are replaced by a unique identifier so that the expression
    can be parsed by the normal Python parser, then the IDs are replaced with the custom
    #nodes.Closure AST node.
    """

    self.log.debug('_parse_expr()')

    token = ProxyToken(self.tokenizer)

    # We don't want to ignore whitespace while parsing Python statements.
    with token.set_skipped(Token.Whitespace, False):

      parts: t.List[str] = []  # Code snippets in this statement.
      control_stack: t.List[str] = []  # Stack of grouping control characters (e.g. parentheses, contains the closing variant ")]}" ).
      closures: t.Dict[str, nodes.Closure] = {}

      while token and token.tv not in self.EXPRESSION_DELIMITERS:
        if (not control_stack or control_stack[-1] != '}') and token.tv == (Token.Control, ':'):
          # Colons are only expected as part of the expression when used inside curly braces.
          break

        closure_def = self._parse_closure()
        if closure_def:
          closures[closure_def.id] = closure_def
          if parts:
            parts.append(' ')
          parts.append(closure_def.id)
          continue

        macro = self._try_parse_macro()
        if macro:
          macro_result = macro.parse(self, expect_expression=bool(parts))
          if isinstance(macro_result, list):
            if parts:
              raise RuntimeError('macro cannot return a stmt inside an expression')
            raise NotImplementedError('todo')  # TODO(NiklasRosenstein)
          elif isinstance(macro_result, ast.expr):
            parts.append(astor.to_source(macro_result))
          else:
            assert False, type(macro_result)

        if token.type == Token.Control and token.value in '([{':
          control_stack.append({'(': ')', '[': ']', '{': '}'}[token.value])
        elif token.type == Token.Control and token.value in ')]}':
          if not control_stack:
            break
          if control_stack[-1] != token.value:
            raise syntax_error(
            msg='unbalanced parentheses',
            filename=self.filename,
            line=token.pos.line,
            col=token.pos.column + 1,
            text=self.tokenizer.scanner.getline(token.pos))
          control_stack.pop()
        elif (token.type == Token.Newline or token.tv == (Token.Control, ';') or
              token.tv == (Token.Control, '=')) and not control_stack and \
            set(parts) not in (set(), {'\n'}):
          break

        parts.append(token.value)
        token.next()

    code = ''.join(parts).strip()
    if not code:
      return None
    self.log.debug('_parse_expr() code: %r', code)
    stmt = ast.parse(code, self.filename, 'eval')
    if not isinstance(stmt, ast.Expression):
      raise RuntimeError('expected expr, got %s' % stmt)  # TODO(NiklasRosenstein)
    return stmt.body

  def _parse_expr_expected(self) -> ast.expr:
    expr = self._parse_expr()
    if expr is None:
      raise SyntaxError(self.filename, self.tokenizer.scanner.pos.line, 'expected expression',
        self.tokenizer.scanner.pos.column, True, 'expected expression')
    return expr

  def _parse_expected_token(self, tv: t.Tuple[Token, str]) -> None:
    if self.tokenizer.current.tv == tv:
      self.tokenizer.next()
    else:
      raise SyntaxError(self.filename, self.tokenizer.scanner.pos.line, 'expected ' + str(tv),
        self.tokenizer.scanner.pos.column, True, 'expected ' + str(tv))

  def _parse_decorated_stmt(self, current_indent: int) -> ast.stmt:
    """
    Parses a decorated statement (i.e., either a class or function definition).
    """

    token = ProxyToken(self.tokenizer)
    assert token.tv == (Token.Control, '@')

    #target = self._parse_name()
    if token.tv == (Token.Control, '('):
      pass
    raise NotImplementedError('decorator')  # TODO(NiklasRosenstein)

  def _parse_block_stmt(self, current_indent: int) -> ast.stmt:
    """
    Parses a block statement (i.e. one introduced by a Python keyword like `def`, `if` or
    `class`). The tokenizer must be positioned on the opening keyword of the block.
    """

    token = self.tokenizer.current
    assert token.type == Token.Name and token.value in self.PYTHON_KEYWORDS

    if token.value == 'if':
      return self._parse_if(current_indent)
    elif token.value == 'while':
      return self._parse_while()
    elif token.value == 'for':
      return self._parse_for()
    elif token.value == 'class':
      return self._parse_class()
    elif token.value == 'def':
      return self._parse_def()
    if token.value == 'pass':
      self.tokenizer.next()
      return ast.Pass()
    raise NotImplementedError(token.value)

  def _parse_if(self, current_indent: int) -> ast.If:
    """
    Parses an if statement.
    """

    token = ProxyToken(self.tokenizer)
    assert token.tv == (Token.Name, 'if')
    token.next()

    root: t.Optional[ast.If] = None
    last: t.Optional[ast.If] = None
    keyword = 'if'

    while True:
      if keyword in ('if', 'elif'):
        cond = self._parse_expr_expected()
        self._parse_expected_token((Token.Control, ':'))
        body = self._parse_stmt_block(current_indent)
        if_stmt = ast.If(cond, body, [])
        if last:
          last.orelse = [if_stmt]
        else:
          root = if_stmt
        last = if_stmt
      elif keyword == 'else':
        assert last is not None
        self._parse_expected_token((Token.Control, ':'))
        body = self._parse_stmt_block(current_indent)
        last.orelse = body
      else:
        assert False, keyword

      # Peek ahead if we have a elif/else.
      state = token.save()
      if token.type == Token.Indent and len(token.value) == current_indent:
        token.next()
        if token.tv in ((Token.Name, 'elif'), (Token.Name, 'else')):
          keyword = token.value
          token.next()
          continue
      token.load(state)
      break

    assert root
    return root

  def _parse_stmt_line(self, parent_indent: int) -> t.List[ast.stmt]:  # NOSONAR
    """
    Parses a statement from the current position of the tokenizer, but at least a full line in the
    source file. If a new block is opened by the statement, that block is parsed recursively.
    """

    self.log.debug('_parse_stmt_line()')

    stmts: t.List[ast.stmt] = []
    token = ProxyToken(self.tokenizer)
    while token and token.type != Token.Newline:
      if token.tv == (Token.Control, '@'):
        stmts.append(self._parse_decorated_stmt(parent_indent))
      elif token.type == Token.Name and token.value in self.PYTHON_KEYWORDS:
        stmts.append(self._parse_block_stmt(parent_indent))
      else:
        # Parse what could be in the left side of an assignment or be just an expression.
        # TODO(NiklasRosenstein): Support parsing potentially multiple assignment targets and type hints.
        node: t.Optional[ast.expr] = self._parse_expr()
        if node is not None and token.tv == (Token.Control, '='):
          token.next()
          right = self._parse_expr()
          if right is not None:
            stmts.append(ast.Assign([node], right))
            node = None
        if node is not None:
          stmts.append(ast.Expr(node))

      if token.tv != (Token.Control, ';'):
        break
      token.next()

    return stmts

  def _parse_stmt_block(self, parent_indent: int, allow_deindent: bool = True) -> t.List[ast.stmt]:  # NOSONAR
    """
    Parses a sequence of Python statements, and continues recursively for new statements that
    introduce new blocks (like `if`, `class`, `def`, etc.). Some statements may be on the same
    line as the block-opener. In that case, only a single line of statements is parsed.
    """

    self.log.debug('_parse_stmt_block()')

    is_same_line = (self._skip_comments() == 0)
    if is_same_line:
      return self._parse_stmt_line(parent_indent)

    token = ProxyToken(self.tokenizer)
    current_indent = len(token.value) if token.type == Token.Indent else 0
    assert current_indent > parent_indent
    stmts: t.List[ast.stmt] = []
    while token:
      line_indent = len(token.value) if token.type == Token.Indent else 0
      if not allow_deindent and line_indent < current_indent:
        state = token.save()
        if token.type == Token.Indent:
          token.next()
        if token.tv == (Token.Control, '}'):  # CLosure closing brace
          break
        token.load(state)
      if (line_indent < current_indent and not allow_deindent) or (line_indent > current_indent):
        raise syntax_error(
          msg='bad indentation: ' + str(token()),
          filename=self.filename,
          line=token.pos.line,
          col=token.pos.column + 1,
          text=self.tokenizer.scanner.getline(token.pos),
          cls=IndentationError)
      if line_indent != current_indent:
        break
      if token.type == Token.Indent:
        token.next()
      line_stmts = self._parse_stmt_line(current_indent)
      if not line_stmts:
        break
      stmts.extend(line_stmts)
      self._skip_comments()

    return stmts

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

    self.log.debug('_parse_closure()')

    token = ProxyToken(self.tokenizer)
    state = token.save()
    arglist = self._parse_closure_header()
    body: t.Optional[t.List[ast.stmt]] = None
    expr: t.Optional[ast.expr] = None
    closure_id = ''.join(self._closure_stack) + f'_closure_{self._closure_counter + 1}'
    self._closure_stack.append(closure_id)

    if token.tv == (Token.Control, '{'):
      body = self._parse_closure_body()
    if body is None and arglist:
      # We only parse an expression for the Closure body if an arglist was specified.
      expr = self._parse_expr()

    assert self._closure_stack.pop() == closure_id

    if not (body or expr):
      # NOTE(NiklasRosenstein): We could raise our own SyntaxError here if an arglist was provided
      #     as that is a strong indicator that a Closure expression or body should be provided,
      #     but we can also just leave the complaining to the Python parser.
      token.load(state)
      return None

    self._closure_counter += 1
    return nodes.Closure(closure_id, arglist, body, expr)

  def _parse_closure_body(self) -> t.Optional[t.List[ast.stmt]]:
    """
    Parses the body of a closure, expecting to start with the opening curly brace. The method will
    detect if the expression is actually a dictionary literal or comprehension and return #None in
    that case.
    """

    token = ProxyToken(self.tokenizer)
    state = token.save()

    if token.tv != (Token.Control, '{'):
      return None
    token.next()

    stmts = self._parse_stmt_block(parent_indent=-1, allow_deindent=False)

    if token.tv != (Token.Control, '}'):
      token.load(state)
      return None
    token.next()

    return stmts

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

  def _try_parse_macro(self) -> t.Optional[Macro]:
    return None  # TODO(NiklasRosenstein)

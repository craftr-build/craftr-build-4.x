
import ast
import json
import typing as t

import yaml
from nr.parsing.core import Lexer, Scanner  # type: ignore

from ..parser import Parser, Token
from .. import util
from . import MacroPlugin


class YamlMacro(MacroPlugin):

  def parse_macro(self, parser: Parser, lexer: Lexer) -> ast.expr:
    loc = parser.location()
    with lexer.disabled(Token.WHITESPACE):
      lexer.next()
      if lexer.token.tv != (Token.CONTROL, '{'):
        parser.error(ast.expr, Token.CONTROL, '{')
      lexer.next()
      if lexer.token.type != Token.NEWLINE:
        parser.error(ast.expr, Token.NEWLINE)

    indent: t.Optional[int] = None
    lines: t.List[str] = []
    while True:
      whitespace = lexer.scanner.match(r'\s*').group(0)
      cursor = lexer.scanner.cursor
      remainder = lexer.scanner.readline()
      if remainder == '\n':
        lines.append('\n')
        continue
      if indent is None and not whitespace:
        parser.error(ast.expr, Token.WHITESPACE, cursor=lexer.scanner.cursor)
      if indent is None:
        indent = len(whitespace)
      elif len(whitespace) < indent:
        lexer.scanner.restore(cursor)
        break
      lines.append(whitespace + remainder)

    lexer.next()
    if lexer.token.tv != (Token.CONTROL, '}'):
      parser.error(ast.expr, Token.CONTROL, '}')
    lexer.next()

    # TODO(NiklasRosenstein): Catch YAML parse error and raise it with parser.error() instead.
    data = yaml.safe_load(''.join(lines))
    node = util.compile_snippet(json.dumps(data), lineno=loc.lineno, col_offset=loc.colno)[0]
    return t.cast(ast.expr, node)

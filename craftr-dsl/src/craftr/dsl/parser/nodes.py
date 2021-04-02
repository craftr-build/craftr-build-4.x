
"""
The Craftr AST is represented as subclasses of the Python #ast module classes'. The Craftr
transpiler can convert these custom node definitions to pure Python standard AST nodes.
"""

import ast
import typing as t


class Closure(ast.expr):
  """
  Represents a closure definition in the Craftr DSL. The transpiler will convert this into a
  decorated function definition in the parent scope.
  """

  _fields = ('id', 'parameters', 'body', 'expr')

  #: A unique ID for the closure, usually derived from the number of closures that have already
  #: been parsed in the same file or it's parent closures.
  id: str

  #: The parameter names of the closure. May be `None` to indicate that closure had no header.
  parameters: t.Optional[t.List[str]]

  #: The body of the closure. May be `None` if the closure body is not constructed using curly
  #: braces to encapsulate multiple statements. In that case, the #expr field is set instead.
  body: t.Optional[t.List[ast.stmt]]

  #: Only set if the body of the closure is just an expression.
  expr: t.Optional[ast.expr]


class LocalDef(ast.stmt):
  """
  Represents a local variable definition in the Craftr DSL. The transpiler will convert this into
  a normal #ast.Assign statement. (#ast.Assign statements that co-exist with #LocalDef statements
  are transpiled into assignments for the current closure).
  """

  _fields = ('name', 'expr')

  name: str
  expr: ast.expr

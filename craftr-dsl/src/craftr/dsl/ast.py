
import ast as pyast
import types
import typing as t
from dataclasses import dataclass, field

import astor  # type: ignore


@dataclass
class Location:
  """
  Represents a location in a file, uniquely identified by a filename and offset. The line- and
  column number are derived metadata.
  """

  filename: str
  offset: int
  lineno: int
  colno: int


@dataclass
class Node:
  """
  Base class for Craftr DSL AST nodes.
  """

  #: The node's parsing location.
  loc: Location = field(repr=False)


@dataclass
class Lambda(Node):
  """
  Represents a Lambda expression that was parsed from inside a Python expression. The lambda
  is replaced with a call to `__lambda_def__("<lambda_id>")` in the same location.
  """

  id: str
  fdef: pyast.FunctionDef

  def __repr__(self):
    return f'Lambda(func={astor.to_source(self.fdef)!r}'


@dataclass
class Expr(Node):
  """
  Represents a Python expression.
  """

  lambdas: t.List[Lambda]
  expr: pyast.Expression

  def __repr__(self):
    return f'Expr(lambdas={self.lambdas!r}, code={astor.to_source(self.expr)!r}'


@dataclass
class Target(Node):
  """
  A target is any valid Python identifier plus (for attribute access).
  """

  name: str

  def set(self, context: t.Union[t.Dict, t.Any], value: t.Any) -> None:
    parts = self.name.split('.')
    for part in parts[:-1]:
      if isinstance(context, t.Mapping):
        context = context[part]
      else:
        context = getattr(context, part)
    if isinstance(context, t.MutableMapping):
      context[parts[-1]] = value
    else:
      setattr(context, parts[-1], value)

  def get(self, context: t.Union[t.Dict, t.Any]) -> t.Any:
    parts = self.name.split('.')
    for part in parts:
      if isinstance(context, t.Mapping):
        context = context[part]
      else:
        context = getattr(context, part)
    return context


@dataclass
class Call(Node):
  """
  A call node allows you to call a function in the current context and optionally entering a new
  context for the return value of that function. The syntax is as follows:

      <Call-Expr> ::= '(' [ <Expr> ( ',' <Expr> )* ] ','? ')'
      <Call>      ::= <Target> [ <Call-Expr> ] '{' <Stmt>* '}' |
                      <Target> <Call-Expr>

  In the below example, we call the function `buildscript()` on the current context (which in the
  case of the Craftr build script is a #Project instance at the root level). The `buildscript()`
  function returns a #Buildscript object, and inside the block we set the #dependencies attribute
  to a list of Python package names.

      buildscript {
        dependencies = [ "craftr-python" ]
      }
  """

  #: The target of the block call expression.
  target: Target

  #: Lambda definitions needed for the call.
  lambdas: t.List[Lambda]

  #: A Python expression that evaluates to the tuple of arguments for the target.
  args: t.Optional[t.List[pyast.expr]]

  #: A list of statements to execute in the block.
  body: t.List[Node]


@dataclass
class Assign(Node):
  """
  Assign a value to a member of the current context. The syntax is as follows:

      <Assign> ::= <Target> '=' <Expr>
  """

  #: The target of the assignment.
  target: Target

  #: THe value to assign.
  value: Expr


@dataclass
class Let(Node):
  """
  Define variable, independent of the current context. On lookup, variable take precedence over
  context members. The syntax is as follows:

      <Let> ::= 'let' <Assign>
  """

  target: Target
  value: Expr


@dataclass
class Module(Node):
  body: t.List[Node]


"""
Transpile Craftr DSL code to full fledged Python code.
"""

import ast
import logging
import typing as t
from dataclasses import dataclass
from .rewrite import Closure, Rewriter


@dataclass
class TranspileOptions:
  """ Options for transpiling Craftr DSL code. """

  preamble: str = 'from craftr.core.closure import closure\n'
  closure_def_prefix: str = '@closure(__closure__)\n'
  closure_arguments_prefix: str = '__closure__, '


def transpile_to_ast(code: str, filename: str, options: t.Optional[TranspileOptions] = None) -> ast.Module:
  rewrite = Rewriter(code, filename).rewrite()
  module = ast.parse(rewrite.code, filename, mode='exec', type_comments=False)
  return ClosureRewriter(filename, options or TranspileOptions(), rewrite.closures).visit(module)


def transpile_to_source(code: str, filename: str, options: t.Optional[TranspileOptions] = None) -> str:
  from astor import to_source
  return to_source(transpile_to_ast(code, filename, options))


class ClosureRewriter(ast.NodeTransformer):
  """
  Rewrites references to closure variables and injects Closure function definitions.
  """

  log = logging.getLogger(__module__ + '.' + __qualname__)  # type: ignore

  def __init__(self, filename: str, options: TranspileOptions, closures: t.Dict[str, Closure]) -> None:
    self.filename = filename
    self.options = options
    self.closures = closures

    # Keep track of the hierarchy during the visitation.
    self._hierarchy: t.List[ast.AST] = []

    # Marks the statement nodes in the hierarchy with the closure name(s) to insert.
    self._closure_inserts: t.Dict[ast.stmt, t.List[str]] = {}

  def _get_closure_def(self, closure_id: str) -> ast.FunctionDef:
    """
    Generate a function definition for a closure id.
    """

    closure = self.closures[closure_id]
    arglist = ', '.join(closure.parameters or [])
    function_code = f'{self.options.closure_def_prefix}def {closure_id}(' \
        f'{self.options.closure_arguments_prefix}{arglist}):\n'
    function_code = '\n' * (function_code.count('\n') + closure.line) + function_code
    if closure.expr:
      function_code += ' ' * closure.indent + 'return ' + closure.expr
    else:
      function_code += closure.body

    self.log.debug('_get_closure_def(%r): parse function body\n\n%s\n', closure_id,
        '  ' + '\n  '.join(function_code.lstrip().splitlines()))

    module = ast.parse(function_code, self.filename, mode='exec', type_comments=False)
    func = module.body[0]
    assert isinstance(func, ast.FunctionDef)
    return func

  def visit_Name(self, name: ast.Name) -> ast.Name:
    if name.id in self.closures:
      for node in self._hierarchy:
        if isinstance(node, ast.stmt):
          self._closure_inserts.setdefault(node, []).append(name.id)
          break
    return name

  def visit_Module(self, node: ast.Module) -> ast.Module:
    preamble = ast.parse(self.options.preamble, self.filename, mode='exec')
    node.body[0:0] = preamble.body
    return self.generic_visit(node)

  def visit(self, node: ast.AST) -> t.Any:
    self._hierarchy.append(node)
    try:
      result: t.Union[ast.AST, t.List[ast.AST]] = super().visit(node)
      if node in self._closure_inserts:
        result = [result]
        for closure_id in self._closure_inserts.get(node, []):
          result.insert(len(result)-1, self._get_closure_def(closure_id))
      return result
    finally:
      assert self._hierarchy.pop() == node

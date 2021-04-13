
"""
Transpile Craftr DSL code to full fledged Python code.
"""

import ast
import logging
import typing as t
from contextlib import contextmanager
from dataclasses import dataclass
from .rewrite import Closure, Rewriter


@dataclass
class TranspileOptions:
  """ Options for transpiling Craftr DSL code. """

  closure_target: str = '__closure__'
  pure_builtins: t.Set[str] = frozenset(['__closure_decorator__'])
  preamble: str = 'from craftr.core.closure import closure as __closure_decorator__\n'
  closure_def_prefix: str = '@__closure_decorator__(__closure__)\n'
  closure_arguments_prefix: str = '__closure__, '
  local_vardef_prefix: str = '_def_'


def transpile_to_ast(code: str, filename: str, options: t.Optional[TranspileOptions] = None) -> ast.Module:
  rewrite = Rewriter(code, filename).rewrite()
  module = ast.parse(rewrite.code, filename, mode='exec', type_comments=False)
  module = ClosureRewriter(filename, options or TranspileOptions(), rewrite.closures).visit(module)
  module = NameRewriter(options or TranspileOptions()).visit(module)
  return ast.fix_missing_locations(module)


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
      for node in reversed(self._hierarchy):
        if isinstance(node, ast.stmt):
          self._closure_inserts.setdefault(node, []).append(name.id)
          break
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
          raise RuntimeError('did not find inner statement to inject closure')
    return self.generic_visit(name)

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
          func = self.visit(self._get_closure_def(closure_id))
          result.insert(len(result)-1, func)
      return result
    finally:
      assert self._hierarchy.pop() == node


class NameRewriter(ast.NodeTransformer):
  """ Rewrites names be accessed through a global object. """

  def __init__(self, options: TranspileOptions) -> None:
    self.options = options
    self._hierarchy: t.List[ast.AST] = []
    self._defined_locals: t.List[t.Set[str]] = [set()]

  def _add_to_locals(self, varnames: t.Set[str]) -> None:
    assert self._defined_locals, 'no locals in current scope'
    self._defined_locals[-1].update(varnames)

  @contextmanager
  def _with_locals(self, varnames: t.Set[str]) -> t.Iterator[None]:
    self._defined_locals.append(varnames)
    try:
      yield
    finally:
      self._defined_locals.pop()

  @contextmanager
  def _with_locals_from_target(self, target: ast.expr) -> t.Iterator[None]:
    names: t.Set[str] = set()
    if isinstance(target, ast.Name):
      names.add(target.id)
    elif isinstance(target, (ast.List, ast.Tuple)):
      names.update(n.id for n in target.elts)
    else:
      raise TypeError(f'expected Name/List/Tuple, got {type(target).__name__}')
    with self._with_locals(names):
      yield

  def _has_local(self, varname: str) -> bool:
    if self._defined_locals:
      return varname in self._defined_locals[-1]
    return False

  def _has_nonlocal(self, varname: str) -> bool:
    for locals in self._defined_locals:
      if varname in locals:
        return True
    return varname == self.options.closure_target or varname in self.options.pure_builtins

  def visit_Name(self, node: ast.Name) -> ast.Expr:
    if self._has_nonlocal(node.id):
      return node
    return ast.Subscript(
      value=ast.Name(id=self.options.closure_target, ctx=ast.Load()),
      slice=ast.Constant(value=node.id),
      ctx=node.ctx)

  def visit_Assign(self, assign: ast.Assign) -> ast.Name:
    if len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name):
      name = assign.targets[0]
      if name.id.startswith(self.options.local_vardef_prefix):
        name.id = name.id[len(self.options.local_vardef_prefix):]
        self._add_to_locals({name.id})
    return self.generic_visit(assign)

  def visit_For(self, node: ast.For) -> ast.For:
    with self._with_locals_from_target(node.target):
      return self.generic_visit(node)

  def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
    self._add_to_locals({node.name})
    names: t.Set[str] = set()
    for arg in node.args.args:
      names.add(arg.arg)
    for arg in node.args.kwonlyargs:
      names.add(arg.arg)
    if node.args.vararg:
      names.add(node.args.vararg.arg)
    if node.args.kwarg:
      names.add(node.args.kwarg.arg)
    with self._with_locals(names):
      return self.generic_visit(node)

  def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
    self._add_to_locals({node.name})
    return self.generic_visit(node)

  def visit_Import(self, node: ast.Import) -> ast.Import:
    names: t.Set[str] = set()
    for name in node.names:
      if name.asname:
        names.add(name.asname)
      else:
        names.add(name.name.rpartition('.')[-1])
    self._add_to_locals(names)
    return self.generic_visit(node)

  def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
    self.visit_Import(ast.Import(names=node.names))  # Dispatch name detection
    return self.generic_visit(node)

  # TODO(NiklasRosenstein): Handle more nodes that define local variables and := operator.

  def visit(self, node: ast.AST) -> ast.AST:
    self._hierarchy.append(node)
    try:
      return super().visit(node)
    finally:
      assert self._hierarchy.pop() == node

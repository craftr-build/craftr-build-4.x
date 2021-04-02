
import ast
import sys
import typing as t


def module(body: t.List[ast.stmt]) -> ast.Module:
  node = ast.Module(body)
  if sys.version >= '3.8':
    node.type_ignores = []  # type: ignore
  return node


def arguments(args: t.List[ast.arg]) -> ast.arguments:
  node = ast.arguments(
      args=args,
      vararg=None,
      kwonlyargs=[],
      kw_defaults=[],
      kwarg=None,
      defaults=[])
  if sys.version >= '3.8':
    node.posonlyargs = []  # type: ignore
  return node


def function_def(
  name: str,
  args: t.List[str],
  body: t.Sequence[ast.AST],
  decorator_list: t.Optional[t.List[ast.expr]] = None,
  lineno: t.Optional[int] = None,
  col_offset: t.Optional[int] = None,
) -> ast.FunctionDef:
  """
  Helper function to create a function def.
  """

  node = ast.FunctionDef(
    name=name,
    args=arguments([ast.arg(x, None) for x in args]),
    body=body,
    decorator_list=decorator_list or [],
    lineno=lineno,
    col_offset=col_offset)
  ast.fix_missing_locations(node)
  return node


def name_expr(
  name: str,
  ctx: ast.expr_context,
  lineno: t.Optional[int] = None,
  col_offset: t.Optional[int] = None
) -> ast.expr:
  """
  Helper function to parse a name/attribute access/indexing to an AST node.
  """

  node = t.cast(ast.Expression, ast.parse(name, mode='eval')).body
  if hasattr(node, 'ctx'):
    node.ctx = ctx  # type: ignore
  if lineno is not None:
    node.lineno = lineno
  if col_offset is not None:
    node.col_offset = col_offset
  ast.fix_missing_locations(node)
  return node


def compile_snippet(
  snippet: str,
  lineno: t.Optional[int] = None,
  col_offset: t.Optional[int] = None,
  mode: str = 'exec',
) -> t.Sequence[ast.AST]:
  """
  Compile a snippet into a Python AST.
  """

  node = ast.parse(snippet, filename='<input>', mode=mode)

  # Will be fixed later down the road with #ast.fix_missing_locations().
  for child in ast.walk(node):
    if hasattr(child, 'lineno'):
      if lineno is None:
        del child.lineno
      else:
        child.lineno = lineno
    if hasattr(child, 'col_offset'):
      if col_offset is None:
        del child.col_offset
      else:
        child.col_offset = col_offset

  if mode == 'exec':
    return t.cast(ast.Module, node).body

  elif mode == 'eval':
    node = t.cast(ast.Expression, ast.parse(snippet, mode='eval'))
    return [node.body]

  else:
    raise ValueError(f'bad mode: {mode!r}')

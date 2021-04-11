
"""
Transpile Craftr DSL code to full fledged Python code.
"""

import ast
import typing as t
from dataclasses import dataclass
from .rewrite import Rewriter


@dataclass
class TranspileOptions:
  """ Options for transpiling Craftr DSL code. """

  preamble: str = 'from craftr.core.closure import closure\n'
  closure_decoration: str = '@closure(__closure__)'
  closure_arguments_prefix: str = '__closure__, '


def transpile_to_ast(code: str, filename: str, options: t.Optional[TranspileOptions] = None) -> ast.Module:
  rewrite = Rewriter(code, filename).rewrite()
  module = ast.parse(rewrite.code, filename, mode='exec', type_comments=False)
  return module


def transpile_to_source(code: str, filename: str, options: t.Optional[TranspileOptions] = None) -> str:
  from astor import to_source
  return to_source(transpile_to_ast(code, filename, options))


"""
This package implements the Craftr DSL laguage.
"""

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.1.2'

import ast
import sys
import typing as t
from pathlib import Path

from craftr.core.closure import Closure

from .parser.parser import CraftrParser


def parse_file(path: Path) -> ast.AST:
  return CraftrParser(path.read_text(), str(path)).parse()


def execute_file(path: Path, owner: t.Any) -> None:
  module = parse_file(path)
  scope = {'closure': Closure(lambda: None, sys._getframe(1))}
  exec(compile(module, str(path)), scope)

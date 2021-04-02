
import ast
import abc
import pkg_resources
import typing as t

if t.TYPE_CHECKING:
  from ..parser import Parser
  from ..transpiler import Transpiler
  from nr.parsing.core import Lexer  # type: ignore


class MacroPlugin(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def parse_macro(self, parser: 'Parser', lexer: 'Lexer') -> ast.expr:
    """
    Parse a macro from the lexer's current position. The lexer is pointing to the token that
    introduces the macro. A custom node can be returned if a #MacroTranspilerPlugin is registered
    for the node type.
    """


GROUP_ID = 'craftr.dsl.macros'


def get_macro_plugin(name: str) -> t.Type[MacroPlugin]:
  """
  Load a macro plugin by it's entrypoint name.
  """

  try:
    ep = next(pkg_resources.iter_entry_points(GROUP_ID, name))
  except StopIteration:
    raise ValueError(f'unknown macro {name!r}')

  cls = ep.load()
  if not issubclass(cls, MacroPlugin):
    raise RuntimeError(f'macro plugin {name!r} does not inherit from MacroPlugin')

  return cls

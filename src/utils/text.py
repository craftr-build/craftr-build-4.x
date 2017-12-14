"""
A bunch of text processing utilities.
"""

import argparse
import textwrap


def reindent(text, indent=''):
  """
  Uses #textwrap.dedent() to on *text*, then splits it by lines to add the
  string *indent* before every line. Returns the new *text* with the new
  indentation.
  """

  lines = textwrap.dedent(text).split('\n')
  while lines and not lines[0].strip():
    lines.pop(0)
  while lines and not lines[-1].strip():
    lines.pop()
  return indent + ('\n' + indent).join(lines)


class ReindentHelpFormatter(argparse.HelpFormatter):

  def __init__(self, *a, **kw):
    super().__init__(*a, **kw)
    self._max_help_position = self._width // 2

  def _fill_text(self, text, width, indent):
    # Called to format the description.
    return reindent(text, '  ')

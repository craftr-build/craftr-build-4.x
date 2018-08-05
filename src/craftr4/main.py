
import argparse

from craftr4.api.globals import _session_stack, session
from craftr4.api.session import Session


def get_argument_parser(prog=None):
  parser = argparse.ArgumentParser(prog=prog)
  return parser


def main(argv=None, prog=None):
  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)

  _session_stack.push(Session())
  with session.enter_scope('main', '1.0-0'):
    with open('build.craftr') as fp:
      import types
      m = types.ModuleType('build')
      exec(compile(fp.read(), 'build.craftr', 'exec'), vars(m))


if __name__ == '__main__':
  main()

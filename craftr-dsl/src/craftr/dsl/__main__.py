
import argparse
import importlib
import os
import sys

import astor  # type: ignore

from . import execute, transpile_to_source

parser = argparse.ArgumentParser(prog=os.path.basename(sys.executable) + ' -m craftr.dsl')
parser.add_argument('file', nargs='?')
parser.add_argument('-c', '--context', metavar='ENTRYPOINT')
parser.add_argument('-E', '--transpile', action='store_true')


def main():
  args = parser.parse_args()

  if args.transpile:
    if args.context:
      parser.error('conflicting arguments: -c/--context and -E/--transpile')

  if args.file:
    with open(args.file) as fp:
      code = fp.read()
    filename = args.file
  else:
    code = sys.stdin.read()
    filename = '<stdin>'

  if args.transpile:
    print(transpile_to_source(code, filename))
    return

  if args.context:
    module_name, member = args.context.partition(':')
    context = getattr(importlib.import_module(module_name), member)()
  else:
    context = None

  globals_ = {'self': context} if context is not None else {}
  execute(code, filename, globals_)


if __name__ == '__main__':
  main()

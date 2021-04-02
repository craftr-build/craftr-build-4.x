
import argparse
import importlib
import os
import sys

import astor  # type: ignore

from . import run_file, compile_file
from .macros import get_macro_plugin

parser = argparse.ArgumentParser(prog=os.path.basename(sys.executable) + ' -m craftr.dsl')
parser.add_argument('file', nargs='?')
parser.add_argument('-c', '--context', metavar='ENTRYPOINT')
parser.add_argument('-E', '--transpile', action='store_true')
parser.add_argument('-m', '--macros', default=[], action='append')

class VoidContext:
  pass


def main():
  args = parser.parse_args()
  macros = {m: get_macro_plugin(m)() for m in args.macros}

  if args.transpile:
    if args.context:
      parser.error('conflicting arguments: -c/--context and -E/--transpile')

    module = compile_file(args.file or '<stdin>', sys.stdin if not args.file else None, macros=macros)
    print(astor.to_source(module))
    return

  if args.context:
    module_name, member = args.context.partition(':')
    context = getattr(importlib.import_module(module_name), member)()
  else:
    context = VoidContext()

  run_file(context, {}, args.file or '<stdin>', sys.stdin if not args.file else None, macros=macros)


if __name__ == '__main__':
  main()

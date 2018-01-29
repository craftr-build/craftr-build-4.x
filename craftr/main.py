
import argparse
import sys


def get_argument_parser():
  parser = argparse.ArgumentParser(prog='craftr')
  return parser


def _main(argv=None):
  parser = get_argument_parser()
  args = parser.parse_args(argv)
  print('Hello, world!')
  return 0


def main():
  sys.exit(_main())

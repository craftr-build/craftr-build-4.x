
import argparse
import os
import sys

from .dsl import Parser


class Session:
  """
  Implements searching for modules and caching them.
  """

  def __init__(self):
    self.path = ['.', os.path.join(os.path.dirname(__file__), 'lib')]
    self.parsed_modules = {}
    self.loaded_modules = {}

  def find_module(self, name):
    if name in self.parsed_modules:
      return self.parsed_modules[name]
    for path in self.path:
      filename = os.path.join(path, name + '.craftr')
      if os.path.isfile(filename):
        break
      filename = os.path.join(path, name, 'build.craftr')
      if os.path.isfile(filename):
        break
    else:
      raise ValueError("Unable to find module {!r}".format(name))
    with open(filename) as fp:
      project = Parser().parse(fp.read())
    if project.name != name:
      raise RuntimeError('project name ({}) does not match path which it was found in ({})'
        .format(project.name, name))
    self.parsed_modules[name] = project
    return project

  def load_module(self, name):
    if name in self.loaded_modules:
      return self.loaded_modules[name]
    project = self.find_module(name)
    raise NotImplementedError


def get_argument_parser():
  parser = argparse.ArgumentParser(prog='craftr')
  parser.add_argument('-f', '--file', default='build.craftr', help='The Craftr build script to execute.')
  return parser


def _main(argv=None):
  parser = get_argument_parser()
  args = parser.parse_args(argv)

  with open(args.file) as fp:
    project = Parser().parse(fp.read())
  project.render(sys.stdout, 0)

  return 0


def main():
  sys.exit(_main())

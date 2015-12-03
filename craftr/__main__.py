# Copyright (C) 2015  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
''' That's what happens when you run Craftr. '''

import argparse
import craftr
import errno
import importlib
import os


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-m', help='The name of a Craftr module to run.')
  args = parser.parse_args()

  if not args.m:
    if not os.path.isfile('Craftfile'):
      print('error: "Craftfile" does not exist')
      return errno.ENOENT
    args.m = craftr.ext.get_module_ident('Craftfile')
    if not args.m:
      print('error: "Craftfile" has no craftr_module(...) declaration')
      return errno.ENOENT

  craftr.ext.install()
  with craftr.magic.enter_context(craftr.session, craftr.Session()):
    module = importlib.import_module('craftr.ext.' + args.m)


if __name__ == '__main__':
  main()

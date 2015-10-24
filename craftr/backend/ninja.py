# Copyright (C) 2015 Niklas Rosenstein
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

from craftr.utils.shell import quote, call
from craftr.vendor import ninja_syntax
import craftr

import argparse
import re
import sys


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('outfile', nargs='?', default='build.ninja',
    help='The output file. Defaults to "build.ninja". Pass "-" to output '
      'to stdout instead.')
  return parser.parse_args()


def main(args, session, module):
  if args.outfile == '-':
    _export(sys.stdout, session, ())
  else:
    session.info('ninja export ({})...'.format(quote(args.outfile)))
    with open(args.outfile, 'w') as fp:
      _export(fp, session, ())


def ident(name):
  ''' Generates a valid ninja identifier from a Craftr target
  identifier. '''

  return re.sub('[^A-Za-z0-9_\.]+', '_', name)


def _export(fp, session, default_targets):
  writer = ninja_syntax.Writer(fp, width=4096)
  writer.comment('this file was automatically created by craftr-{0}'.format(craftr.__version__))
  writer.comment('it is not recommended to modify it manually.')
  writer.comment('visit https://github.com/craftr-build/craftr for more information.')
  writer.newline()

  for module in sorted(session.modules.values(), key=lambda x: x.identifier):
    if not module.targets:
      continue

    if module.pools:
      writer.comment("'{0}' Pools".format(module.identifier))
      writer.newline()
    for pool in sorted(module.pools.values(), key=lambda x: x.name):
      writer.pool(ident(pool.identifier), pool.depth)
    if module.pools:
      writer.newline()

    if module.targets:
      writer.comment("'{0}' Targets".format(module.identifier))
      writer.newline()

    for target in sorted(module.targets.values(), key=lambda x: x.name):
      if len(target.commands) != 1:
        session.error('Ninja export currently supports only one command')

      rule = ident(target.identifier)

      command = ' '.join(quote(x) for x in target.commands[0])
      command = command.replace(craftr.IN, '$in')
      command = command.replace(craftr.OUT, '$out')

      desc = target.description or ''
      desc = desc.replace(craftr.IN, '$in')
      desc = desc.replace(craftr.OUT, '$out')

      if target.pool is None or target.pool == 'console':
        pool = target.pool
      else:
        pool = ident(target.pool.identifier)

      writer.rule(rule, command, pool=pool, description=desc)
      writer.newline()

      if target.foreach:
        if len(target.inputs) != len(target.outputs):
          session.error("target '{}': number of input files must match "
            "the number of output files".format(target.identifier))
        for infile, outfile in zip(target.inputs, target.outputs):
          writer.build([outfile], rule, [infile], implicit=target.requires)
      elif target.inputs:
        writer.build(target.outputs, rule, target.inputs, implicit=target.requires)

      writer.build(rule, 'phony', target.outputs)
      writer.newline()

  if default_targets:
    defaults = set()
    for target in default_targets:
      defaults |= set(target.outputs)
    writer.default(list(defaults))

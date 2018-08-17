# -*- coding: utf8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2018  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import os
import requests
import sys

parser = argparse.ArgumentParser()
parser.add_argument('to')
parser.add_argument('url')
parser.add_argument('--makedirs', action='store_true')


def main(argv=None):
  args = parser.parse_args(argv)
  if not args.url:
    parser.error('missing required option --url')
  if not args.to:
    parser.error('missing required option --to')
  if args.makedirs:
    os.makedirs(os.path.dirname(args.to), exist_ok=True)
  response = requests.get(args.url, stream=True)
  try:
    response.raise_for_status()
  except requests.RequestException as e:
    print(e, file=sys.stderr)
    return 1
  with open(args.to, 'wb') as fp:
    for chunk in response.iter_content(2048):
      fp.write(chunk)
  return 0


if __name__ == '__main__':
  sys.exit(main())

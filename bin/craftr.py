#!/usr/bin/env python3
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
''' Script to run Craftr on Windows. Since the suffix is `.py`, it would
import itself on `import craftr`, therefore the script removes all paths
from `sys.path` that contain a `craftr.py` file. '''

import os
import sys

# Remove all paths that contain exactly this file. It would import itself
# instead of the craftr module.
for path in sys.path[:]:
  ref_file = os.path.join(path, 'craftr.py')
  if os.path.isfile(ref_file):
    sys.path.remove(path)

# If this script is run from the Craftr repositories' script/ folder,
# we will add the repository to the search path.
dirname = os.path.dirname(__file__)
repo_path = os.path.dirname(dirname)
if os.path.exists(os.path.join(repo_path, 'craftr', '__init__.py')):
  sys.path.append(repo_path)

import craftr.__main__
if __name__ == "__main__":
  sys.exit(craftr.__main__.main())

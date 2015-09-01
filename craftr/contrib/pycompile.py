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
'''
This file must be Python 2 and 3 compatible and it may be directly
executed as a python script. It provides functions that allow the
invokation of this script from various Python versions to allow the
compilation of python modules and files.
'''

from __future__ import print_function

import os
import pipes
import py_compile
import re
import subprocess
import sys
import zipfile


def quote(s):
  if os.name == 'nt' and os.sep == '\\':
    s = s.replace('"', '\\"')
    if re.search('\s', s):
      s = '"' + s + '"'
    return s
  else:
    return pipes.quote(s)


def shell(command, **kwargs):
  if isinstance(command, (list, tuple)):
    command = ' '.join(quote(x) for x in command)
  return subprocess.call(command, shell=True, **kwargs)


def bytecompile(pybin, source, outdir=None, real_deal=False):
  ''' Compiles the specified *source* file or package directory to the
  output file (or package directry) to the specified output directory
  *outdir*. Regardless of PEP 3147, this will always place the byte
  compiled files in the old-style place. '''

  if not real_deal:
    if outdir is None:
      outdir = os.path.dirname(source)
    command = [pybin, __file__, 'bytecompile', source, outdir]
    return shell(command)

  def recurse(filename, basedir):
    if os.path.isfile(filename) and filename.endswith('.py'):
      cfile = filename[:-3] + '.pyc'
      cfile = os.path.join(outdir, os.path.relpath(cfile, basedir))
      print("  [c]", os.path.relpath(filename))
      py_compile.compile(filename, cfile)
    elif os.path.isdir(filename):
      for item in os.listdir(filename):
        recurse(os.path.join(filename, item), basedir)

  print("Bytecompiling", os.path.relpath(source))
  recurse(source, os.path.dirname(source))


def makeegg(source, dest, exclude_source=True):
  ''' Creates a Python Egg (without EGG-INFO) from the specified *source*
  python module or package and save it to *dest*. If *exclude_source* is
  True, source files will be excluded from the egg.

  If *source* is a list, its items are assumed to be filenames instead
  that are all supposed to be packed into the output egg. '''

  if isinstance(source, str):
    source = [source]

  # List of files to be put into the egg, with their relative
  # filename as second items of the tuple.
  files = set()

  def process(filename, basedir):
    basename = os.path.basename(filename)
    if basename == '__pycache__':
      return
    if os.path.isdir(filename):
      for item in os.listdir(filename):
        process(os.path.join(filename, item), basedir)
    elif os.path.isfile(filename):
      try:
        source_file, byte_file = get_py_pair(filename)
      except ValueError:
        return  # not a Python file

      if os.path.isfile(byte_file):
        files.add((byte_file, os.path.relpath(byte_file, basedir)))
      if not exclude_source and os.path.isfile(source_file):
        files.add((source_file, os.path.relpath(source_file, basedir)))
    else:
      raise OSError('"{0}" does not exist'.format(filename))

  for path in source:
    path = os.path.abspath(path)
    process(path, os.path.dirname(path))

  dirname = os.path.dirname(dest)
  if not os.path.exists(dirname):
    os.makedirs(dirname)

  print("Creating python egg at", dest)
  egg = zipfile.ZipFile(dest, 'w')
  for filename, arcname in files:
    print("  [+]", os.path.relpath(filename), "({0})".format(arcname))
    egg.write(filename, arcname)


def bdist_egg(pybin, package, outdir, exclude_source=True):
  ''' Assuming *package* is the path to a directory that contains a
  `setup.py` script, this script will generate a Python binary egg
  distribution of the package to the specified *outdir*. '''

  if not os.path.isdir(outdir):
    os.makedirs(outdir)
  command = [pybin, 'setup.py', 'bdist_egg', '--dist-dir', outdir]
  if exclude_source:
    command.append('--exclude-source-files')
  return shell(command, cwd=package)


def bdist(pybin, package, outdir, exclude_source=True):
  ''' Runs the bdist_egg command, but specifiy *outdir* as the
  temporary build directory and keeps the build result. This basically
  results in an unzipped egg at *outdir*. '''

  if not os.path.isdir(outdir):
    os.makedirs(outdir)
  print(package)
  command = [pybin, 'setup.py', 'bdist_egg', '-b', outdir, '-k']
  res = shell(command, cwd=package)
  if res != 0:
    return res
  # if exclude_source:
  #   purge(outdir, '.py')
  return 0


def get_py_pair(filename):
  ''' Given the filename of a Python source or byte compiled filename,
  returns a pair of the source and byte compiled filename. '''

  if filename.endswith('.py'):
    filename = filename[:-3]
  elif filename.endswith('.pyc'):
    filename = filename[:-4]
  else:
    raise ValueError('filename does not end with .py or .pyc')

  return (filename + '.py', filename + '.pyc')


def purge(directories, suffix='.pyc'):
  ''' Purge the specified *directories* and all its subfolders from
  byte-compile python cache folders. *directories* may also be a string
  of a single directory. '''

  if isinstance(directories, str):
    directories = [directories]

  def recurse(dirname):
    for item in os.listdir(dirname):
      item = os.path.join(dirname, item)
      if item.endswith(suffix) and os.path.isfile(item):
        os.remove(item)
      elif os.path.isdir(item):
        recurse(item)

  for dirname in directories:
    if os.path.isdir(dirname):
      recurse(dirname)


def main():
  if sys.argv[1] == 'bytecompile':
    bytecompile(None, sys.argv[2], sys.argv[3], real_deal=True)
  else:
    print("error: Unexpected command", sys.argv[1], file=sys.stderr)


if __name__ == "__main__":
  main()

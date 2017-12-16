# Copyright (c) 2017 Niklas Rosenstein
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
"""
A small tool to augment the MANIFEST.MF in a JAR file and add files to it or
remove files from it.
"""

import argparse
import codecs
import contextlib
import os
import shutil
import sys
import zipfile


def parse_manifest(fp):
  """
  Parses a Java manifest file.
  """

  for line in fp:
    if ':' not in line: continue
    yield line.rstrip().partition(':')[::2]


def write_manifest(fp, data):
  """
  Writes a Java manifest file.
  """

  for key, value in data.items():
    fp.write('{}: {}\n'.format(key, value))


def main():
  parser = argparse.ArgumentParser(description="Augment/merge JAR files.")
  parser.add_argument('jar', help='The input JAR file.')
  parser.add_argument('-o', '--output', help='The output JAR file.')
  parser.add_argument('-a', '--append', help='Append a manifest property.',
      metavar='KEY=VALUE', action='append', default=[])
  parser.add_argument('-s', '--set', help='Set a manifest property.',
      metavar='KEY=VALUE', action='append', default=[])
  parser.add_argument('-f', '--put-file', help='Add a file to the JAR archive. If '
      'the file already exists in the JAR, an error is printed and the '
      'operation is aborted, unless --overwrite is specified.',
      metavar='ARCNAME=FILENAME', action='append', default=[])
  parser.add_argument('-r', '--rem-file', help='Remove a file from the JAR archive. '
      'If the file does not exist, an error is printed unless --force is '
      'specified.', action='append', default=[], metavar='ARCNAME')
  parser.add_argument('-m', '--merge', help='Merge the specified JAR file '
      'into the current JAR. Note that the META-INF/ directory will be '
      'skipped during the merge process. If files are duplicate, an error '
      'will occur.', metavar='JARFILE', action='append', default=[])
  parser.add_argument('--overwrite', action='store_true', help='Don\'t error '
      'with --put-file when a file already exists.')
  parser.add_argument('--force', action='store_true', help='Don\'t error '
      'with --rem-file if the file does not exist in the JAR.')
  parser.add_argument('-v', '--verbose', action='store_true')
  args = parser.parse_args()

  if not args.output:
    print('fatal: -o,--output must be specified.')
    sys.exit(1)

  for fname in args.merge:
    if not os.path.isfile(fname):
      print('fatal: no such file or directory: {!r}'.format(fname))
      sys.exit(1)

  put_files = {}
  rem_files = args.rem_file
  add_values = []
  set_values = []

  for string in args.put_file:
    arcname, __, filename = string.partition('=')
    if not arcname or not filename:
      print('fatal: invalid --put-file argument: {!r}'.format(string))
      sys.exit(1)
    if not os.path.exists(filename):
      print('fatal: no such file or directory: {!r}'.format(filename))
      sys.exit(1)
    put_files[arcname] = filename

  for string in args.append:
    key, sep, value = string.partition('=')
    if not key or not sep:
      print('fatal: invalid --add argument: {!r}'.format(string))
      sys.exit(1)
    add_values.append((key, value))

  for string in args.set:
    key, sep, value = string.partition('=')
    if not key or not sep:
      print('fatal: invalid --set argument: {!r}'.format(string))
      sys.exit(1)
    set_values.append((key, value))

  original = None
  try:
    with contextlib.suppress(FileExistsError):
      os.makedirs(os.path.dirname(args.output) or '.')

    # Rename the original file temporarily.
    if os.path.isfile(args.output):
      original = args.output + '~temprename'
      os.rename(args.output, original)
      if args.verbose:
        print('renamed original file "{}" temporarily'.format(os.path.basename(args.output)))

    utf8reader = codecs.getreader('utf8')
    utf8writer = codecs.getwriter('utf8')
    with zipfile.ZipFile(args.jar, mode='r') as injar, \
         zipfile.ZipFile(args.output, mode='w') as outjar:
      namelist = injar.namelist()

      # Read the manifest file.
      manifest = utf8reader(injar.open('META-INF/MANIFEST.MF'))
      manifest = dict(parse_manifest(manifest))

      # Augment the file.
      for key, value in add_values:
        if key not in manifest:
          manifest[key] = value
        else:
          manifest[key] += value
      for key, value in set_values:
        manifest[key] = value

      # Check if the files that are to be removed actually exist.
      for arcname in rem_files:
        if arcname not in namelist:
          print('fatal: JAR does not contain "{}", can not be removed'.format(arcname))
          sys.exit(1)

      # A list of the files already added to the archive.
      collected_names = []

      # Copy all files to the output archive.
      for current in [(injar, namelist)] + args.merge:
        with contextlib.ExitStack() as stack:
          if isinstance(current, str):
            # A JAR file from the list of files to merge.
            curr_jar = stack.enter_context(zipfile.ZipFile(current, 'r'))
            curr_namelist = curr_jar.namelist()
            skip_meta_inf = True
          else:
            # The original input JAR file.
            curr_jar, curr_namelist = current
            skip_meta_inf = False

          for name in curr_namelist:
            if skip_meta_inf and name.startswith('META-INF/'):
              continue
            if not name.endswith('/') and name in collected_names:
              print('fatal: duplicate entry: {!r}'.format(name))
              continue

            # Check if one of the rem_files excludes this file by a whole
            # directory.
            excluded = any(name == x or (x.endswith('/') and name.startswith(x))
                          for x in rem_files)
            if excluded:
              if args.verbose:
                print('skipped:', name)
              continue
            if name in put_files:
              if args.verbose:
                print('skipped (from {}):'.format(put_files[name]), name)
              continue
            if name.endswith('/'):
              continue

            # Special case, write the manifest data that we modified.
            if name == 'META-INF/MANIFEST.MF':
              with outjar.open(name, 'w') as fp:
                write_manifest(utf8writer(fp), manifest)

            # Otherwise just copy the whole file contents.
            else:
              with curr_jar.open(name) as src, outjar.open(name, 'w') as dst:
                shutil.copyfileobj(src, dst)

            if args.verbose:
              print('copied:', name)

        collected_names += curr_namelist

      # Write all new files into the archive.
      for name, source in put_files.items():
        with open(source, 'rb') as src, outjar.open(name, 'w') as dst:
          shutil.copyfileobj(src, dst)
        if args.verbose:
          print('copied:', name, '(from {})'.format(source))

    if original:
      os.remove(original)
  except:
    with contextlib.suppress(FileNotFoundError):
      os.remove(args.output)
    if original:
      os.rename(original, args.output)
    raise


if require.main == module:
  main()

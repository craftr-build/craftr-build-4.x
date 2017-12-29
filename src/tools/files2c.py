
import argparse
import itertools
import os
import re
import struct
import sys


def grouper(iterable, n, fillvalue=None):
  args = [iter(iterable)] * n
  return itertools.zip_longest(*args, fillvalue=fillvalue)


parser = argparse.ArgumentParser()
parser.add_argument('-o', '--output', metavar='FILE')
parser.add_argument('files', nargs='+', help='One or more files. Optionally, '
  'the filename may be suffixed with :<cname> to specify the file\'s name in '
  'the C source file.')


def main(argv=None):
  args = parser.parse_args(argv)
  with open(args.output, 'w') as dst:
    print(args.output)
    dst.write('#include <stdint.h>\n')
    for fname in args.files:
      drive, fname = os.path.splitdrive(fname)
      fname, sep, cname = fname.partition(':')
      if not sep and not cname:
        cname = re.sub('[^\w\d_]+', '_', os.path.basename(fname))
      fname = drive + fname

      with open(fname, 'rb') as src:
        data = src.read()
      dst.write('size_t {}_size = {};\n'.format(cname, len(data)))
      dst.write('unsigned char {}[] = {{\n'.format(cname))
      for b in data:
        dst.write('{0:#08x}, '.format(b))
      dst.write('\n};\n')


if require.main == module:
  sys.exit(main())


import argparse
import os
import requests
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--url')
parser.add_argument('--to')
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


if require.main == module:
  sys.exit(main())

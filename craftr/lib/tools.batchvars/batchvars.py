"""
Runs a batch file and outputs the environment variables after that batch file
has run as a JSON object.
"""

import json
import subprocess
import sys
import os
from craftr import sh


def batchvars(batchfile, *args):
  key = 'JSONOUTPUTBEGIN:'
  pyprint = 'import os, json; print("{}" + json.dumps(dict(os.environ)))'
  pyprint = pyprint.format(key)

  cmd = [batchfile] + list(args)
  cmd.extend([sh.safe('&&'), sys.executable, '-c', pyprint])
  output = subprocess.check_output(sh.join(cmd), shell=True).decode()

  key = 'JSONOUTPUTBEGIN:'
  index = output.find(key)
  if index < 0:
    raise ValueError('failed: ' + cmd + '\n\n' + output)

  env = json.loads(output[index + len(key):])
  return env


def main(argv=None):
  if argv is None:
    argv = sys.argv[1:]
  print(json.dumps(batchvars(*argv), sort_keys=True, indent=2))
  return 0

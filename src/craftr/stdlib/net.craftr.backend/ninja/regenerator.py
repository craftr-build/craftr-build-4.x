
import sys
import os

idx_inputs = sys.argv.index('INPUTS:')
idx_outputs = sys.argv.index('OUTPUTS:')
idx_command = sys.argv.index('COMMAND:')

inputs = sys.argv[idx_inputs+1:idx_outputs]
outputs = sys.argv[idx_outputs+1:idx_command]
command = sys.argv[idx_command+1:]

# Check if the files are actually dirty.
import nr.fs
if nr.fs.compare_all_timestamps(inputs, outputs):
  import subprocess
  sys.exit(subprocess.call(command))
else:
  print('Skipping re-generate step, not dirty.')

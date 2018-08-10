import os

def rm(*filenames, dir=False, recursive=False, force=False):
  # TODO: Windows support with del command
  flags = ''
  if dir: flags += 'd'
  if recursive: flags += 'r'
  if force: flags += 'f'
  command = ['rm']
  if flags: command += ['-' + flags]
  command += filenames
  return command

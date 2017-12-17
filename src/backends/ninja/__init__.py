
import io
import nodepy
import os
import re
import requests
import shlex
import shutil
import subprocess
import sys
import zipfile

import craftr from 'craftr'
import {Writer as NinjaWriter} from './ninja_syntax'

NINJA_FILENAME = 'ninja' + ('.exe' if os.name == 'nt' else '')
NINJA_MIN_VERSION = '1.7.1'
if sys.platform.startswith('win32'):
  NINJA_PLATFORM = 'win'
elif sys.platform.startswith('darwin'):
  NINJA_PLATFORM = 'mac'
else:
  NINJA_PLATFORM = 'linux'
NINJA_URL = 'https://github.com/ninja-build/ninja/releases/download/v1.8.2/ninja-{}.zip'.format(NINJA_PLATFORM)


def quote(s, for_ninja=False):
  """
  Enhanced implementation of :func:`shlex.quote` as it generates single-quotes
  on Windows which can lead to problems.
  """

  if os.name == 'nt' and os.sep == '\\':
    s = s.replace('"', '\\"')
    if re.search('\s', s) or any(c in s for c in '<>'):
      s = '"' + s + '"'
  else:
    s = shlex.quote(s)
  if for_ninja:
    # Fix escaped $ variables on Unix, see issue craftr-build/craftr#30
    s = re.sub(r"'(\$\w+)'", r'\1', s)
  return s


def make_rule_description(node):
  commands = [' '.join(map(quote, x)) for x in node.commands]
  return ' && '.join(commands)


def make_rule_name(graph, node):
  return re.sub('[^\d\w\-_\.]+', '_', node.name)


def check_ninja_version(build_directory, download=False):
  # If there's a local ninja version, use it.
  local_ninja = os.path.join(build_directory, NINJA_FILENAME)
  if os.path.isfile(local_ninja):
    ninja = local_ninja
  elif not craftr.options.get('ninja.local_install', False):
    # Otherwise, check if there's a ninja version installed.
    ninja = shutil.which('ninja')
  else:
    ninja = None

  # Check the minimum Ninja version.
  if ninja:
    ninja_version = subprocess.check_output([ninja, '--version']).decode().strip()
    if not ninja_version or ninja_version < NINJA_MIN_VERSION:
      print('note: need at least ninja {} (have {} at "{}")'.format(NINJA_MIN_VERSION, out, ninja))
      ninja = None
      ninja_version = None

  if not ninja and download:
    # Download a new Ninja version into the build directory.
    ninja = local_ninja
    print('note: downloading Ninja ({})'.format(NINJA_URL))
    with zipfile.ZipFile(io.BytesIO(requests.get(NINJA_URL).content)) as zfile:
      with zfile.open(NINJA_FILENAME) as src:
        with open(ninja, 'wb') as dst:
          shutil.copyfileobj(src, dst)
      os.chmod(ninja, int('766', 8))
    ninja_version = subprocess.check_output([ninja, '--version']).decode().strip()

  if not download and ninja_version:
    print('note: Ninja v{} ({})'.format(ninja_version, ninja))
  return ninja


def prepare_build(build_directory, graph, args):
  check_ninja_version(build_directory, download=True)
  build_file = os.path.join(build_directory, 'build.ninja')
  if os.path.exists(build_file) and os.path.getmtime(build_file) >= graph.mtime():
    return  # Does not need to be re-exported, as the build graph hasn't changed.

  print('note: writing "{}"'.format(build_file))
  with open(build_file, 'w') as fp:
    writer = NinjaWriter(fp, width=9000)
    writer.comment('This file was automatically generated by Craftr')
    writer.comment('It is not recommended to edit this file manually.')
    writer.newline()

    # writer.variable('msvc_deps_prefix')  # TODO
    writer.variable('builddir', build_directory)
    writer.variable('nodepy_exec_args', ' '.join(map(quote, nodepy.runtime.exec_args)))
    writer.newline()

    non_explicit = []
    for node in sorted(graph.nodes(), key=lambda x: x.name):
      phony_name = make_rule_name(graph, node)
      rule_name = 'rule_' + phony_name
      if not node.explicit:
        non_explicit.append(phony_name)

      command = [
        '$nodepy_exec_args',
        str(require.resolve('craftr/main').filename),
        '--build-directory', build_directory,
        # Place the hash in the command string, so Ninja always knows when
        # when the definition of the build node changed.
        '--run-node', '{}^{}'.format(node.name, graph.hash(node)),
      ]
      order_only = []
      for dep in [graph[x] for x in node.deps]:
        #if not dep.output_files:
          order_only.append(make_rule_name(graph, dep))
        #else:
        #  order_only.extend(dep.output_files)

      command = ' '.join(quote(x, for_ninja=True) for x in command)
      writer.rule(rule_name, command, description=make_rule_description(node), pool = 'console' if node.console else None)
      writer.build(
        outputs = node.output_files or [phony_name],
        rule = rule_name,
        inputs = node.input_files,
        order_only = order_only)
      if node.output_files:
        writer.build([phony_name], 'phony', node.output_files)
      writer.newline()

    if non_explicit:
      writer.default(non_explicit)


def build(build_directory, graph, args):
  ninja = check_ninja_version(build_directory)
  if not ninja:
    return 1
  command = [ninja, '-f', os.path.join(build_directory, 'build.ninja')]
  command += args.build_args
  command += [make_rule_name(graph, node) for node in graph.selected()]
  subprocess.run(command)


def clean(build_directory, graph, args):
  ninja = check_ninja_version(build_directory)
  if not ninja:
    return 1

  if args.recursive:
    targets = [make_rule_name(graph, node) for node in graph.selected()]
  else:
    # Use -r and passing rules only cleans files that have been created by that rule.
    targets = ['rule_' + make_rule_name(graph, node) for node in graph.selected()]
    if targets:
      targets.insert(0, '-r')

  command = [ninja, '-f', os.path.join(build_directory, 'build.ninja'), '-t', 'clean']
  command += args.clean_args
  command += targets
  subprocess.run(command)

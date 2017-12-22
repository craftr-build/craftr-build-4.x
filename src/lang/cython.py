"""
Compile Cython projects with Craftr.
"""

import functools
import json
import os
import subprocess
import craftr, {path} from 'craftr'
import cxx from 'craftr/lang/cxx'
import sh from 'craftr/utils/sh'

cython_bin = sh.split(craftr.options.get('cython.cython', os.getenv('CYTHON', 'cython')))
python_bin = sh.split(craftr.options.get('cython.python', os.getenv('PYTHON', 'python')))


def get_python_config(python_bin):
  # TODO: Cache result
  pyline = 'import json, distutils.sysconfig; '\
    'print(json.dumps(distutils.sysconfig.get_config_vars()))'
  command = python_bin + ['-c', pyline]
  output = subprocess.check_output(command, shell=True).decode()
  result = json.loads(output)
  result['_PYTHON_BIN'] = python_bin
  return result


def python_prebuilt(*, name=None, python_bin):
  config = get_python_config(python_bin)

  if not name:
    name = 'python' + config['VERSION']
    try:
      return craftr.cell().targets[name]
    except KeyError:
      pass

  # LIBDIR seems to be absent from Windows installations, so we
  # figure it from the prefix.
  if os.name == 'nt' and 'LIBDIR' not in config:
    config['LIBDIR'] = path.join(config['prefix'], 'libs')

  target = cxx.prebuilt(
    name = name,
    includes = [config['INCLUDEPY']],
    libpath = [config['LIBDIR']],
    syslibs = [],
  )

  # The name of the Python library is something like "libpython2.7.a",
  # but we only want the "python2.7" part. Also take the library flags
  # m, u and d into account (see PEP 3149).
  if 'LIBRARY' in config:
    lib = re.search('python\d\.\d(?:d|m|u){0,3}', config['LIBRARY'])
    if lib:
      target.trait.syslibs.append(lib.group(0))
  elif os.name == 'nt':
    # This will make pyconfig.h nominate the correct .lib file.
    target.trait.defines = ['MS_COREDLL']

  return target


@craftr.TargetFactory
class transpile(craftr.TargetTrait):

  def __init__(self,
               srcs,
               python_bin=None,
               py_version=None,
               cpp=False,
               embed=False,
               fast_fail=False,
               includes=None,
               additional_flags=None):
    self.srcs = [path.canonical(craftr.localpath(x)) for x in srcs]
    self.python_bin = python_bin or globals()['python_bin']
    self.py_version = py_version
    self.cpp = cpp
    self.embed = embed
    self.fast_fail = fast_fail
    self.includes = includes or []
    self.additional_flags = additional_flags or []
    self.pyconf = get_python_config(self.python_bin)

    outdir = path.join(self.target.cell.build_directory, 'cython-src')
    self.output_files = craftr.relocate_files(
        self.srcs, outdir, '.cpp' if self.cpp else '.c',
        parent=self.target.cell.directory)

  def translate(self):
    if self.py_version is None:
      self.py_version = int(get_python_config(self.python_bin)['VERSION'][0])
    if self.py_version not in (2, 3):
      raise ValueError('invalid py_version: {!r}'.format(self.py_version))

    command = cython_bin + ['$in', '-o', '$out', '-{}'.format(self.py_version)]
    command += ['-I' + x for x in self.includes]
    command += ['--fast-fail'] if self.fast_fail else []
    command += ['--cplus'] if self.cpp else []
    if isinstance(self.embed, str):
      command += ['--embed=' + self.embed]
    elif self.embed == True:
      command += ['--embed']
    elif self.embed != False:
      raise ValueError('cython.build.embed must be str or boolean, got {}'
          .format(type(self.embed).__name__))
    command += self.additional_flags
    self.target.add_action(craftr.BuildAction(
      name = 'cython',
      commands = [command],
      input_files = self.srcs,
      output_files = self.output_files,
      foreach = True
    ))



def project(*,
            name,
            # transpile
            srcs,
            python_bin=None,
            py_version=None,
            cpp=False,
            #embed=False,
            fast_fail=False,
            includes=None,
            additional_flags=None,
            # transpile main
            main=None,
            # cxx build
            in_working_tree=False,
            defines=None,
            cxx_build_options=None):
  if srcs:
    trns = transpile(
      name = name + '_transpile',
      srcs = srcs,
      python_bin = python_bin,
      py_version = py_version,
      cpp = cpp,
      embed = False,
      fast_fail = fast_fail,
      includes = includes,
      additional_flags = additional_flags
    )
  if main:
    trns_main = transpile(
      name = name + '_transpile_main',
      srcs = [main],
      python_bin = python_bin,
      py_version = py_version,
      cpp = cpp,
      embed = True,
      fast_fail = fast_fail,
      includes = includes,
      additional_flags = additional_flags,
    )

  cell = craftr.cell()
  def gen_libname(filename):
    if in_working_tree:
      return path.rmvsuffix(filename)
    else:
      return path.join(cell.build_directory, 'cython-bin',
          path.rel(path.rmvsuffix(filename), cell.directory))

  cxx_build_options = cxx_build_options or {}
  cxx_build_options.setdefault('compiler', cxx.compiler)
  pyconf = trns.trait.pyconf
  pylib = python_prebuilt(name = name + '_python_lib', python_bin = pyconf['_PYTHON_BIN'])

  if srcs:
    libfiles = [gen_libname(x)+ pyconf['SO'] for x in trns.trait.srcs]
    lib = cxx.library(
      name = name + '_compile',
      deps = [pylib, trns],
      srcs = trns.trait.output_files,
      outname = libfiles,
      preferred_linkage = 'shared',
      defines = defines,
      localize_srcs = False,
      **cxx_build_options
    )
  else:
    lib = None

  if main:
    bin = cxx.binary(
      name = name + '_compile_main',
      deps = [pylib, trns_main],
      srcs = trns_main.trait.output_files,
      #outname = ,
      defines = defines,
      localize_srcs = False,
      **cxx_build_options
    )
  else:
    bin = None

  return (lib, bin)


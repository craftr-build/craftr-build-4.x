"""
Compile Cython projects with Craftr.
"""

import functools
import json
import os
import subprocess
import craftr, {path, sh} from 'craftr'
import cxx from '@craftr/cxx'

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


def python_prebuilt(*, name=None, parent=None, python_bin):
  config = get_python_config(python_bin)

  if not name:
    name = 'python' + config['VERSION']
    try:
      return craftr.Namespace().current().targets[name]
    except KeyError:
      pass

  # LIBDIR seems to be absent from Windows installations, so we
  # figure it from the prefix.
  if os.name == 'nt' and 'LIBDIR' not in config:
    config['LIBDIR'] = path.join(config['prefix'], 'libs')

  target = cxx.prebuilt(
    name = name,
    parent = parent,
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
      target.impl.syslibs.append(lib.group(0))
  elif os.name == 'nt':
    # This will make pyconfig.h nominate the correct .lib file.
    target.impl.defines = ['MS_COREDLL']

  return target


class CythonCompile(craftr.Behaviour):

  def init(self, srcs, py_version=None, cpp=False, embed=False,
           fast_fail=False, includes=None, additional_flags=None):
    self.srcs = [path.canonical(craftr.localpath(x)) for x in srcs]
    self.py_version = py_version
    self.cpp = cpp
    self.embed = embed
    self.fast_fail = fast_fail
    self.includes = includes or []
    self.additional_flags = additional_flags or []

    outdir = path.join(self.namespace.build_directory, 'cython-src')
    self.output_files = craftr.relocate_files(
        self.srcs, outdir, '.cpp' if self.cpp else '.c',
        parent=self.namespace.directory)

  def translate(self):
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
    self.target.add_action(
      name = 'cython',
      commands = [command],
      input_files = self.srcs,
      output_files = self.output_files,
      foreach = True
    )


class CythonProject(craftr.Behaviour):

  def init(self,
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
        main_outfile=None,
        # cxx build
        in_working_tree=False,
        defines=None,
        cxx_build_options=None):
    self.compile_lib = None
    self.compile_main = None
    self.link_lib = None
    self.link_main = None
    python_bin = python_bin or globals()['python_bin']

    pyconf = get_python_config(python_bin)
    pylib = python_prebuilt(name = 'python_lib', parent = self.target, python_bin = python_bin)
    if not py_version:
      py_version = int(pyconf['VERSION'][0])

    if srcs:
      self.compile_lib = compile(
        name = 'compile_lib',
        parent = self.target,
        srcs = srcs,
        py_version = py_version,
        cpp = cpp,
        embed = False,
        fast_fail = fast_fail,
        includes = includes,
        additional_flags = additional_flags
      )
    if main:
      self.compile_main = compile(
        name = 'compile_main',
        parent = self.target,
        srcs = [craftr.localpath(main)],
        py_version = py_version,
        cpp = cpp,
        embed = True,
        fast_fail = fast_fail,
        includes = includes,
        additional_flags = additional_flags
      )

    def gen_libname(filename):
      if in_working_tree:
        return path.canonical(path.rmvsuffix(filename), self.namespace.build_directory)
      else:
        return path.join(self.namespace.build_directory, path.rel(path.rmvsuffix(filename), self.namespace.directory))

    cxx_build_options = cxx_build_options or {}
    cxx_build_options.setdefault('compiler', cxx.compiler)

    if self.compile_lib:
      libfiles = [gen_libname(x) + pyconf['SO'] for x in self.compile_lib.impl.srcs]
      self.link_lib = cxx.library(
        name = 'link_lib',
        parent = self.target,
        deps = [self.compile_lib, pylib],
        srcs = self.compile_lib.impl.output_files,
        outname = libfiles,
        outdir = None,
        preferred_linkage = 'shared',
        defines = defines,
        localize_srcs = False,
        **cxx_build_options
      )
    if self.compile_main:
      if not main_outfile:
        main_outfile = '{}$(ext)'.format(path.rmvsuffix(path.base(main)))
      self.link_main = cxx.binary(
        name = 'link_main',
        parent = self.target,
        deps = [self.compile_main, pylib] + ([self.link_lib] if self.link_lib else []),
        srcs = self.compile_main.impl.output_files,
        outname = main_outfile,
        outdir = self.namespace.directory if in_working_tree else NotImplemented,
        defines = defines,
        localize_srcs = False,
        **cxx_build_options
      )

  def translate(self):
    pass


compile = craftr.Factory(CythonCompile)
project = craftr.Factory(CythonProject)


def run(target, *args, **kwargs):
  target = craftr.resolve_target(target)
  kwargs.setdefault('name', target.name + '_run')
  if isinstance(target.impl, CythonProject):
    target = target.impl.link_main
  return cxx.run(target, *args, **kwargs)

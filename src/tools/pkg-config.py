
import cxx from 'craftr/lang/cxx'
import sh from 'craftr/utils/sh'


class PkgConfigError(Exception):
  pass


def pkg_config(pkg_name, target_name=None, static=True):
  """
  If available, this function uses ``pkg-config`` to extract flags for
  compiling and linking with the package specified with *pkg_name*. If
  ``pkg-config`` is not available or the it can not find the package,
  :class:`PkgConfigError` is raised.
  """

  command = ['pkg-config', pkg_name, '--cflags', '--libs']
  if static:
    command.append('--static')

  try:
    flags = sh.check_output(command).decode()
  except FileNotFoundError as exc:
    raise PkgConfigError('pkg-config is not available ({})'.format(exc))
  except sh.CalledProcessError as exc:
    raise PkgConfigError('{} not installed on this system\n\n{}'.format(
        pkg_name, exc.stderr or exc.stdout))

  # Parse the flags.
  include = []
  defines = []
  syslibs = []
  libpath = []
  compile_flags = []
  link_flags = []

  for flag in sh.split(flags):
    if flag.startswith('-I'):
      include.append(flag[2:])
    elif flag.startswith('-D'):
      defines.append(flag[2:])
    elif flag.startswith('-l'):
      syslibs.append(flag[2:])
    elif flag.startswith('-L'):
      libpath.append(flag[2:])
    elif flag.startswith('-Wl,'):
      link_flags.append(flag[4:])
    else:
      compile_flags.append(flag)

  return cxx.prebuilt(
    name = target_name or pkg_name,
    includes = include,
    defines = defines,
    syslibs = syslibs,
    libpath = libpath,
    compiler_flags = compile_flags,
    linker_flags = link_flags
  )


pkg_config.Error = PkgConfigError

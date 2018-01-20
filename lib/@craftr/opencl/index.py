
import os, sys
import craftr, {path} from 'craftr'
import cxx from '@craftr/cxx'
import {pkg_config} from '@craftr/pkg-config'

vendor = craftr.options.get('opencl.vendor', None)
if not vendor and sys.platform.startswith('win32'):
  raise EnvironmentError('option not set: opencl.vendor')

if not vendor:
  pkg_config('OpenCL', 'opencl')
elif vendor == 'intel':
  sdk_dir = craftr.options.get('opencl.intel_sdk', None)
  if not sdk_dir:
    sdk_dir = 'C:\\Intel\\OpenCL\\sdk'
  if os.name == 'nt':
    cxx.prebuilt(
      name = 'opencl',
      includes = [path.join(sdk_dir, 'include')],
      libpath = [path.join(sdk_dir, 'lib', cxx.compiler.arch)],
      syslibs = ['OpenCL']
    )
  else:
    raise NotImplementedError('intel on {!r}'.format(sys.platform))
elif vendor == 'nvidia':
  import {sdk_dir} from 'craftr/lang/cuda'
  if os.name == 'nt':
    cxx.prebuilt(
      name = 'opencl',
      includes = [path.join(sdk_dir, 'include')],
      libpath = [path.join(sdk_dir, 'lib', 'Win32' if cxx.compiler.is32bit else 'x64')],
      syslibs = ['OpenCL']
    )
  else:
    raise NotImplementedError('nvidia on {!r}'.format(sys.platform))
elif vendor == 'amd':
  sdk_dir = craftr.options.get('opencl.amd_sdk', None)
  raise NotImplementedError('amd on {!r}'.format(sys.platform))
else:
  raise EnvironmentError('unsupported opencl.vendor: {!r}'.format(vendor))

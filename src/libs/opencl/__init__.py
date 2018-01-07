
namespace = 'craftr/libs/opencl'

import os, sys
import craftr, {path} from 'craftr'
import cxx from 'craftr/lang/cxx'

vendor = craftr.options.get('opencl.vendor', None)
if not vendor:
  raise EnvironmentError('option not set: opencl.vendor')

if vendor == 'intel':
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
  sdk_dir = craftr.options.get('opencl.nvidia_sdk', None)
  raise NotImplementedError('nvidia')
elif vendor == 'amd':
  sdk_dir = craftr.options.get('opencl.amd_sdk', None)
  raise NotImplementedError('amd')
else:
  raise EnvironmentError('unsupported opencl.vendor: {!r}'.format(vendor))

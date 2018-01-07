
namespace = 'craftr/libs/glew'

import craftr, {path} from 'craftr'
import cxx from 'craftr/lang/cxx'

version = craftr.options.get('glew.version', '2.1.0')
binary_dir = craftr.options.get('glew.binary_dir', None)
static = craftr.options.get('glew.static', True)

if cxx.compiler.id in ('msvc', 'mingw'):
  if not binary_dir:
    url = 'https://github.com/nigels-com/glew/releases/download/glew-{version}/glew-{version}-win32.zip'
    url = url.format(version=version)
    binary_dir = craftr.get_source_archive(url)
    binary_dir = path.join(path.abs(binary_dir), 'glew-{}'.format(version))

  cxx.prebuilt(
    name = 'glew',
    includes = [path.join(binary_dir, 'include')],
    libpath = [path.join(binary_dir, 'lib', 'Release', 'Win32' if cxx.compiler.is32bit else 'x64')],
    defines = ['GLEW_STATIC'] if static else [],
    syslibs = [
      'glew32s' if static else 'glew32',
      'user32',
      'opengl32',
      'Ws2_32',
      'ole32',
      'comctl32',
      'gdi32',
      'comdlg32',
      'uuid'
    ]
  )

else:
  raise EnvironmentError('unsupported compiler: {!r}'.format(cxx.compiler.name))


import craftr
from craftr import path

if OS.type == 'nt':
  exe_suffix = '.exe'
else:
  exe_suffix = ''


class HaskellTargetHandler(craftr.TargetHandler):

  def get_common_property_scope(self):
    return 'haskell'

  def setup_target(self, target):
    target.define_property('haskell.srcs', 'StringList', inheritable=False)
    target.define_property('haskell.productName', 'String', inheritable=False)
    target.define_property('haskell.compilerFlags', 'StringList')

  def finalize_target(self, target, data):
    src_dir = target.directory()
    build_dir = path.join(context.build_directory, target.module().name())
    if not data.productName:
      data.productName = target.name() + target.module().version()
    if data.srcs:
      data.srcs = [path.canonical(x, src_dir) for x in data.srcs]
      data.productFilename = path.join(build_dir, data.productName + exe_suffix)
      target.outputs().add(data.productFilename, ['exe'])

  def translate_target(self, target, data):
    if data.srcs:
      # Action to compile the sources to an executable.
      command = ['ghc', '-o', '$out', '$in']
      command += data.compilerFlags
      action = target.add_action('haskell.compile', commands=[command])
      build = action.add_buildset()
      build.files.add(data.srcs, ['in'])
      build.files.add(data.productFilename, ['out'])

      # Action to run the executable.
      command = [data.productFilename]
      action = target.add_action('haskell.run', commands=[command],
        explicit=True, syncio=True, output=False)
      action.add_buildset()


module.register_target_handler(HaskellTargetHandler())


import craftr
from craftr import path

if OS.type == 'nt':
  exe_suffix = '.exe'
else:
  exe_suffix = ''


class ValaTargetHandler(craftr.TargetHandler):

  def get_common_property_scope(self):
    return 'vala'

  def setup_target(self, target):
    target.define_property('vala.srcs', 'StringList', inheritable=False)
    target.define_property('vala.productName', 'String', inheritable=False)
    target.define_property('vala.compilerFlags', 'StringList')
    target.define_property('vala.linkerFlags', 'StringList')

  def finalize_target(self, target, data):
    src_dir = target.directory()
    build_dir = path.join(context.build_directory, target.module().name())
    if not data.productName:
      data.productName = target.name() + '-' + target.module().version()
    if data.srcs:
      data.srcs = [path.canonical(x, src_dir) for x in data.srcs]
      data.productFilename = path.join(build_dir, data.productName + exe_suffix)
      target.outputs().add(data.productFilename, ['exe'])

  def translate_target(self, target, data):
    if data.srcs:
      command = ['valac', '-o', '$out', '$in']
      command += data.compilerFlags
      for flag in data.linkerFlags:
        command += ['-X', flag]
      action = target.add_action('vala.compile', commands=[command])
      build = action.add_buildset()
      build.files.add(data.srcs, ['in'])
      build.files.add(data.productFilename, ['out'])

      command = [data.productFilename]
      action = target.add_action('vala.run', commands=[command],
        explicit=True, syncio=True, output=False)
      action.add_buildset()


module.register_target_handler(ValaTargetHandler())
